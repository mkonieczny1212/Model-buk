from __future__ import annotations

import hashlib
import json
import os
import time
import unicodedata
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from model_buk.catalog import LEAGUES, season_for_date
from model_buk.security import safe_error
from model_buk.team_names import resolve_team_name


FOOTYSTATS_BASE = "https://api.football-data-api.com"
SPORTMONKS_BASE = "https://api.sportmonks.com/v3/football"


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class _DiskJsonCache:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def get(self, key: str, ttl_seconds: int) -> Any | None:
        path = self._path(key)
        if not path.exists() or time.time() - path.stat().st_mtime > ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def put(self, key: str, payload: Any) -> None:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


@dataclass(frozen=True)
class SecondaryProviderStatus:
    name: str
    connected: bool
    role: str
    probability_input: bool
    reason: str | None = None


FOOTYSTATS_NAMES = {
    "EPL": ["Premier League", "England Premier League"],
    "LALIGA": ["La Liga", "LaLiga", "Spain La Liga"],
    "BUNDESLIGA": ["Bundesliga", "Germany Bundesliga"],
    "SERIEA": ["Serie A", "Italy Serie A"],
    "LIGUE1": ["Ligue 1", "France Ligue 1"],
    "EREDIVISIE": ["Eredivisie", "Netherlands Eredivisie"],
    "PRIMEIRA": ["Liga NOS", "Primeira Liga", "Portugal Primeira Liga"],
    "BELGIUM": ["Pro League", "Belgian Pro League", "Belgium Pro League"],
    "SUPERLIG": ["Super Lig", "Süper Lig", "Turkey Super Lig"],
    "EKSTRAKLASA": ["Ekstraklasa", "Poland Ekstraklasa"],
    "UCL": ["UEFA Champions League", "Champions League"],
    "UEL": ["UEFA Europa League", "Europa League"],
    "UECL": ["UEFA Europa Conference League", "UEFA Conference League", "Conference League"],
}


class FootyStatsClient:
    """Secondary current-form / reconciliation provider.

    The client intentionally does NOT feed probabilities directly yet. Its first
    production role is independent current-season reconciliation and gap-filling
    research. Any FootyStats-derived feature must pass the same point-in-time OOS
    gate as every other probability input before it can alter P_model.
    """

    def __init__(self, api_key: str | None = None, cache_dir: str | Path = "runtime/footystats_cache", timeout: int = 12):
        self.api_key = (api_key or os.getenv("FOOTYSTATS_API_KEY") or "").strip()
        self.timeout = timeout
        self.cache = _DiskJsonCache(cache_dir)
        self._session = requests.Session()

    @property
    def connected(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, Any]:
        return SecondaryProviderStatus(
            name="FootyStats",
            connected=self.connected,
            role="current-season reconciliation / xG-process coverage audit",
            probability_input=False,
            reason=None if self.connected else "Brak FOOTYSTATS_API_KEY.",
        ).__dict__

    def _get(self, endpoint: str, params: dict[str, Any] | None = None, ttl: int = 3600) -> dict[str, Any]:
        if not self.connected:
            raise RuntimeError("FootyStats nie jest podłączone. Ustaw FOOTYSTATS_API_KEY.")
        params = {**(params or {}), "key": self.api_key}
        cache_params = {k: v for k, v in params.items() if k != "key"}
        key = endpoint + "?" + "&".join(f"{k}={cache_params[k]}" for k in sorted(cache_params))
        cached = self.cache.get(key, ttl)
        if cached is not None:
            return cached
        try:
            response = self._session.get(FOOTYSTATS_BASE + endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(safe_error(exc)) from None
        if payload.get("success") is False:
            raise RuntimeError("FootyStats rejected the request; check account access and quota")
        self.cache.put(key, payload)
        return payload

    def league_list(self, chosen_only: bool = True) -> list[dict[str, Any]]:
        payload = self._get("/league-list", {"chosen_leagues_only": "true" if chosen_only else None}, ttl=12 * 3600)
        return list(payload.get("data") or [])

    @staticmethod
    def _season_rows(league_row: dict[str, Any]) -> list[dict[str, Any]]:
        seasons = league_row.get("season") or league_row.get("seasons") or []
        return seasons if isinstance(seasons, list) else []

    def resolve_season_id(self, league_code: str, when: datetime | None = None) -> int | None:
        if league_code not in LEAGUES:
            return None
        when = when or datetime.now(timezone.utc)
        target_year = season_for_date(when.year, when.month, LEAGUES[league_code].default_season_start_month)
        target_names = [_norm(x) for x in FOOTYSTATS_NAMES.get(league_code, [LEAGUES[league_code].name])]
        target_country = _norm(LEAGUES[league_code].country)
        best: tuple[float, int] | None = None
        for row in self.league_list(chosen_only=True):
            name = _norm(row.get("name") or row.get("league_name") or row.get("english_name"))
            country = _norm(row.get("country"))
            if not name or name not in target_names:
                continue
            # International competitions use World/Europe depending on provider.
            allowed_countries = {target_country}
            if league_code in {"UCL", "UEL", "UECL"}:
                allowed_countries.update({"europe", "international", "world"})
            if country not in allowed_countries:
                continue
            score = 1.0
            if target_country and country and target_country == country:
                score += 0.08
            if score < 0.75:
                continue
            seasons = self._season_rows(row)
            candidates: list[tuple[int, int]] = []
            for season in seasons:
                try:
                    sid = int(season.get("id"))
                except Exception:
                    continue
                year_raw = season.get("year") or season.get("starting_year") or season.get("season")
                try:
                    year = int(str(year_raw)[:4])
                except Exception:
                    year = -1
                if year == target_year:
                    candidates.append((year, sid))
            if not candidates:
                continue
            _, sid = max(candidates)
            candidate = (score, sid)
            if best is None or candidate[0] > best[0]:
                best = candidate
        return best[1] if best else None

    def league_teams(self, season_id: int, include_stats: bool = True) -> list[dict[str, Any]]:
        payload = self._get(
            "/league-teams",
            {"season_id": int(season_id), "include": "stats" if include_stats else None},
            ttl=4 * 3600,
        )
        return list(payload.get("data") or [])

    def team_state(self, league_code: str, team_name: str) -> dict[str, Any] | None:
        season_id = self.resolve_season_id(league_code)
        if season_id is None:
            return None
        rows = self.league_teams(season_id, include_stats=True)
        names = [(row.get("name") or row.get("cleanName") or row.get("english_name") or "", row) for row in rows]
        resolved, match_score = resolve_team_name(team_name, [name for name, _ in names if name.strip()])
        matches = [row for name, row in names if name == resolved] if resolved else []
        if len(matches) != 1:
            return None
        row = matches[0]
        stats = row.get("stats") if isinstance(row.get("stats"), dict) else row
        wanted = [
            "xg_for_avg_overall", "xg_against_avg_overall", "shotsAVG_overall",
            "shotsOnTargetAVG_overall", "cornersAVG_overall", "cardsAVG_overall",
            "possessionAVG_overall", "foulsAVG_overall", "pointsPerGame",
            "seasonOver25Percentage_overall", "seasonBTTSPercentage_overall",
        ]
        extracted = {k: stats.get(k) for k in wanted if stats.get(k) is not None}
        return {
            "provider": "FootyStats",
            "season_id": season_id,
            "team_id": row.get("id"),
            "team_name": row.get("name") or row.get("cleanName") or team_name,
            "name_match": round(match_score, 3),
            "stats": extracted,
            "model_usage": "reconciliation_only",
        }


class SportmonksClient:
    """Optional secondary provider for coverage/xG/lineup research.

    Fixture IDs are provider-specific, so this adapter does not silently merge a
    Sportmonks fixture into an API-Football fixture. Reconciliation must use
    competition + kickoff + both teams and pass a confidence gate first.
    """

    def __init__(self, api_token: str | None = None, cache_dir: str | Path = "runtime/sportmonks_cache", timeout: int = 12):
        self.api_token = (api_token or os.getenv("SPORTMONKS_API_TOKEN") or "").strip()
        self.timeout = timeout
        self.cache = _DiskJsonCache(cache_dir)
        self._session = requests.Session()

    @property
    def connected(self) -> bool:
        return bool(self.api_token)

    def status(self) -> dict[str, Any]:
        return SecondaryProviderStatus(
            name="Sportmonks",
            connected=self.connected,
            role="xG / advanced fixture data / expected-lineup coverage audit",
            probability_input=False,
            reason=None if self.connected else "Brak SPORTMONKS_API_TOKEN.",
        ).__dict__

    def _get(self, path: str, params: dict[str, Any] | None = None, ttl: int = 3600) -> dict[str, Any]:
        if not self.connected:
            raise RuntimeError("Sportmonks nie jest podłączone. Ustaw SPORTMONKS_API_TOKEN.")
        params = dict(params or {})
        cache_key = path + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
        cached = self.cache.get(cache_key, ttl)
        if cached is not None:
            return cached
        try:
            response = self._session.get(
                SPORTMONKS_BASE + path,
                params=params,
                headers={"Authorization": self.api_token},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(safe_error(exc)) from None
        self.cache.put(cache_key, payload)
        return payload

    def fixtures_by_date(self, date: str, include: str = "participants;statistics;xGFixture;referees") -> list[dict[str, Any]]:
        payload = self._get(f"/fixtures/date/{date}", {"include": include}, ttl=10 * 60)
        return list(payload.get("data") or [])

    def expected_lineup_fixture(self, fixture_id: int) -> dict[str, Any] | None:
        payload = self._get(f"/fixtures/{int(fixture_id)}", {"include": "expectedLineups"}, ttl=10 * 60)
        return payload.get("data")
