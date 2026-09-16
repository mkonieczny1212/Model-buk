from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from model_buk.catalog import API_ID_TO_LEAGUE, LEAGUES, season_for_date


API_BASE = "https://v3.football.api-sports.io"


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    connected: bool
    reason: str | None = None
    requests_today: int | None = None
    requests_limit: int | None = None


class JsonCache:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: str, ttl_seconds: int) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def put(self, key: str, value: Any) -> None:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


class ApiFootballClient:
    """Small, quota-aware API-Football adapter.

    The adapter is optional. Without API_FOOTBALL_KEY the application remains
    usable in historical/manual mode and explicitly reports missing live context.
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str | Path = "runtime/api_cache",
        timeout: int = 12,
    ):
        self.api_key = (api_key or os.getenv("API_FOOTBALL_KEY") or "").strip()
        self.timeout = timeout
        self.cache = JsonCache(cache_dir)
        self._last_headers: dict[str, str] = {}
        self._session = requests.Session()

    @property
    def connected(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, Any]:
        return {
            "name": "API-Football",
            "connected": self.connected,
            "reason": None if self.connected else "Brak API_FOOTBALL_KEY — działa tryb historyczny/manualny.",
            "requests_remaining": self._last_headers.get("x-ratelimit-requests-remaining"),
            "requests_limit": self._last_headers.get("x-ratelimit-requests-limit"),
        }

    def _get(self, endpoint: str, params: dict[str, Any] | None = None, ttl: int = 300) -> dict[str, Any]:
        if not self.connected:
            raise RuntimeError("API-Football nie jest podłączone. Ustaw API_FOOTBALL_KEY.")
        params = {k: v for k, v in (params or {}).items() if v is not None}
        key = endpoint + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
        cached = self.cache.get(key, ttl)
        if cached is not None:
            return cached
        response = self._session.get(
            API_BASE + endpoint,
            params=params,
            headers={"x-apisports-key": self.api_key},
            timeout=self.timeout,
        )
        self._last_headers = {k.lower(): v for k, v in response.headers.items()}
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors") or []
        if errors:
            raise RuntimeError(f"API-Football: {errors}")
        self.cache.put(key, payload)
        return payload

    def fixtures(self, date: str, league_codes: list[str] | None = None) -> list[dict[str, Any]]:
        # Cost-aware: one precise date call, then filter the supported leagues
        # locally. This avoids spending one quota call per league on every refresh.
        target = datetime.fromisoformat(date).date()
        codes = set(league_codes or LEAGUES.keys())
        allowed_ids = {LEAGUES[code].api_football_id: code for code in codes if code in LEAGUES}
        payload = self._get("/fixtures", {"date": str(target)}, ttl=180)
        items: list[dict[str, Any]] = []
        for row in payload.get("response", []):
            league_id = int((row.get("league") or {}).get("id") or 0)
            code = allowed_ids.get(league_id)
            if code:
                items.append(self._normalize_fixture(row, code))
        return sorted(items, key=lambda x: x.get("kickoff") or "")

    def current_season(self, league_code: str) -> int:
        """Resolve the provider-declared current season for a competition.

        We ask /leagues?current=true instead of assuming calendar-year semantics.
        A deterministic calendar fallback is kept only for temporary provider
        failures and is never used to invent a roster.
        """
        if league_code not in LEAGUES:
            raise ValueError(f"Unsupported league: {league_code}")
        spec = LEAGUES[league_code]
        try:
            payload = self._get(
                "/leagues",
                {"id": spec.api_football_id, "current": "true"},
                ttl=60 * 60 * 12,
            )
            rows = payload.get("response", [])
            if rows:
                seasons = rows[0].get("seasons") or []
                current = [x for x in seasons if x.get("current") is True]
                if current:
                    return int(current[-1]["year"])
        except Exception:
            pass
        now = datetime.now(timezone.utc)
        return season_for_date(now.year, now.month, spec.default_season_start_month)

    def teams_for_league(self, league_code: str, season: int | None = None) -> list[dict[str, Any]]:
        """Return only teams registered in the selected competition/season.

        This is the source of truth for the UI team selector. Historical clubs
        are deliberately not mixed into the current-season roster.
        """
        if league_code not in LEAGUES:
            raise ValueError(f"Unsupported league: {league_code}")
        spec = LEAGUES[league_code]
        season = int(season if season is not None else self.current_season(league_code))
        payload = self._get(
            "/teams",
            {"league": spec.api_football_id, "season": season},
            ttl=60 * 60 * 24,
        )
        output: list[dict[str, Any]] = []
        for row in payload.get("response", []):
            team = row.get("team") or {}
            venue = row.get("venue") or {}
            if not team.get("id") or not team.get("name"):
                continue
            output.append({
                "id": int(team["id"]),
                "name": str(team["name"]),
                "code": team.get("code"),
                "country": team.get("country"),
                "logo": team.get("logo"),
                "venue": {
                    "id": venue.get("id"), "name": venue.get("name"),
                    "city": venue.get("city"),
                },
                "league_code": league_code,
                "season": season,
            })
        return sorted(output, key=lambda x: x["name"])

    def fixture(self, fixture_id: int) -> dict[str, Any]:
        payload = self._get("/fixtures", {"id": fixture_id}, ttl=60)
        rows = payload.get("response", [])
        if not rows:
            raise ValueError(f"Nie znaleziono fixture_id={fixture_id}")
        league_id = int(rows[0].get("league", {}).get("id") or 0)
        league = API_ID_TO_LEAGUE.get(league_id)
        return self._normalize_fixture(rows[0], league.code if league else None)

    @staticmethod
    def _normalize_fixture(row: dict[str, Any], league_code: str | None) -> dict[str, Any]:
        fixture = row.get("fixture", {})
        league = row.get("league", {})
        teams = row.get("teams", {})
        goals = row.get("goals", {})
        venue = fixture.get("venue") or {}
        return {
            "fixture_id": fixture.get("id"),
            "kickoff": fixture.get("date"),
            "status": (fixture.get("status") or {}).get("short"),
            "status_long": (fixture.get("status") or {}).get("long"),
            "league_code": league_code,
            "league_id": league.get("id"),
            "league_name": league.get("name"),
            "country": league.get("country"),
            "season": league.get("season"),
            "round": league.get("round"),
            "home": {
                "id": (teams.get("home") or {}).get("id"),
                "name": (teams.get("home") or {}).get("name"),
                "logo": (teams.get("home") or {}).get("logo"),
                "winner": (teams.get("home") or {}).get("winner"),
                "goals": goals.get("home"),
            },
            "away": {
                "id": (teams.get("away") or {}).get("id"),
                "name": (teams.get("away") or {}).get("name"),
                "logo": (teams.get("away") or {}).get("logo"),
                "winner": (teams.get("away") or {}).get("winner"),
                "goals": goals.get("away"),
            },
            "referee": fixture.get("referee"),
            "venue": {"id": venue.get("id"), "name": venue.get("name"), "city": venue.get("city")},
        }


    def league_coverage(self, league_id: int, season: int) -> dict[str, Any]:
        """Return provider-declared coverage for this league-season.

        Coverage flags are advisory: API-Football documents that a true flag does
        not guarantee every field for every individual fixture. Keeping the raw
        object lets the UI distinguish provider capability from actual response
        completeness.
        """
        payload = self._get("/leagues", {"id": league_id, "season": season}, ttl=60 * 60 * 24)
        rows = payload.get("response", [])
        if not rows:
            return {}
        seasons = rows[0].get("seasons") or []
        target = next((x for x in seasons if int(x.get("year") or -1) == int(season)), None)
        return (target or {}).get("coverage") or {}

    def injuries(self, fixture_id: int) -> list[dict[str, Any]]:
        payload = self._get("/injuries", {"fixture": fixture_id}, ttl=60 * 60)
        output = []
        for row in payload.get("response", []):
            output.append({
                "team_id": (row.get("team") or {}).get("id"),
                "team": (row.get("team") or {}).get("name"),
                "player_id": (row.get("player") or {}).get("id"),
                "player": (row.get("player") or {}).get("name"),
                "type": (row.get("player") or {}).get("type"),
                "reason": (row.get("player") or {}).get("reason"),
            })
        return output

    def lineups(self, fixture_id: int) -> list[dict[str, Any]]:
        payload = self._get("/fixtures/lineups", {"fixture": fixture_id}, ttl=15 * 60)
        result = []
        for team in payload.get("response", []):
            start = []
            for entry in team.get("startXI") or []:
                p = entry.get("player") or {}
                start.append({"id": p.get("id"), "name": p.get("name"), "number": p.get("number"), "pos": p.get("pos")})
            result.append({
                "team_id": (team.get("team") or {}).get("id"),
                "team": (team.get("team") or {}).get("name"),
                "formation": team.get("formation"),
                "coach": (team.get("coach") or {}).get("name"),
                "startXI": start,
            })
        return result

    def odds(self, fixture_id: int) -> list[dict[str, Any]]:
        payload = self._get("/odds", {"fixture": fixture_id}, ttl=60 * 30)
        output: list[dict[str, Any]] = []
        for fixture_row in payload.get("response", []):
            update = fixture_row.get("update")
            for bookmaker in fixture_row.get("bookmakers") or []:
                bname = bookmaker.get("name")
                bid = bookmaker.get("id")
                for bet in bookmaker.get("bets") or []:
                    for value in bet.get("values") or []:
                        try:
                            odd = float(value.get("odd"))
                        except (TypeError, ValueError):
                            continue
                        output.append({
                            "bookmaker_id": bid,
                            "bookmaker": bname,
                            "bet_id": bet.get("id"),
                            "bet": bet.get("name"),
                            "value": value.get("value"),
                            "odd": odd,
                            "update": update,
                        })
        return output

    def prediction_benchmark(self, fixture_id: int) -> dict[str, Any] | None:
        payload = self._get("/predictions", {"fixture": fixture_id}, ttl=60 * 60)
        rows = payload.get("response", [])
        if not rows:
            return None
        p = rows[0].get("predictions") or {}
        return {
            "winner": (p.get("winner") or {}).get("name"),
            "win_or_draw": p.get("win_or_draw"),
            "under_over": p.get("under_over"),
            "advice": p.get("advice"),
            "percent": p.get("percent"),
            "note": "External benchmark only — never used as a PURE Model Buk feature.",
        }

    def recent_fixtures(
        self,
        team_id: int,
        last: int = 6,
        league_id: int | None = None,
        season: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"team": team_id, "last": last}
        if league_id is not None:
            params["league"] = int(league_id)
        if season is not None:
            params["season"] = int(season)
        payload = self._get("/fixtures", params, ttl=60 * 30)
        output = []
        for row in payload.get("response", []):
            league_id = int((row.get("league") or {}).get("id") or 0)
            spec = API_ID_TO_LEAGUE.get(league_id)
            output.append(self._normalize_fixture(row, spec.code if spec else None))
        return output

    def fixture_statistics(self, fixture_id: int) -> dict[int, dict[str, float]]:
        payload = self._get("/fixtures/statistics", {"fixture": fixture_id}, ttl=60 * 60 * 24 * 7)
        output: dict[int, dict[str, float]] = {}
        mapping = {
            "shots on goal": "sot",
            "shots off goal": "shots_off",
            "total shots": "shots",
            "blocked shots": "blocked_shots",
            "shots insidebox": "shots_inside_box",
            "shots outsidebox": "shots_outside_box",
            "corner kicks": "corners",
            "yellow cards": "yellow",
            "red cards": "red",
            "fouls": "fouls",
            "ball possession": "possession",
            "offsides": "offsides",
            "goalkeeper saves": "saves",
            "total passes": "passes",
            "passes accurate": "passes_accurate",
            "passes %": "passes_pct",
            "expected_goals": "xg",
            "expected goals": "xg",
        }
        for row in payload.get("response", []):
            team_id = int((row.get("team") or {}).get("id") or 0)
            stats: dict[str, float] = {}
            for item in row.get("statistics") or []:
                stat_type = str(item.get("type") or "").strip().lower()
                key = mapping.get(stat_type)
                if not key:
                    continue
                value = item.get("value")
                if isinstance(value, str) and value.endswith("%"):
                    value = value[:-1]
                try:
                    stats[key] = float(value or 0)
                except (TypeError, ValueError):
                    continue
            if team_id:
                output[team_id] = stats
        return output

    def current_observations(
        self,
        team_id: int,
        last: int = 6,
        max_stat_calls: int = 6,
        league_id: int | None = None,
        season: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent completed matches and their event counts on demand.

        Cost control: fixture list is one call; detailed statistics are capped and
        cached, so dashboard scanning never performs this work automatically.
        """
        fixtures = self.recent_fixtures(team_id, last=last, league_id=league_id, season=season)
        output: list[dict[str, Any]] = []
        detailed_calls = 0
        for fixture in fixtures:
            if fixture.get("status") not in {"FT", "AET", "PEN"}:
                continue
            home = fixture["home"]
            away = fixture["away"]
            is_home = int(home.get("id") or 0) == int(team_id)
            row = {
                "date": fixture.get("kickoff"),
                "fixture_id": fixture.get("fixture_id"),
                "venue": "home" if is_home else "away",
                "goals_for": home.get("goals") if is_home else away.get("goals"),
                "goals_against": away.get("goals") if is_home else home.get("goals"),
                "opponent": away.get("name") if is_home else home.get("name"),
            }
            if detailed_calls < max_stat_calls:
                try:
                    stats = self.fixture_statistics(int(fixture["fixture_id"]))
                    own = stats.get(int(team_id), {})
                    opp_id = int(away.get("id") if is_home else home.get("id"))
                    opp = stats.get(opp_id, {})
                    row.update({
                        "shots_for": own.get("shots"), "shots_against": opp.get("shots"),
                        "sot_for": own.get("sot"), "sot_against": opp.get("sot"),
                        "corners_for": own.get("corners"), "corners_against": opp.get("corners"),
                        "cards_for": (own.get("yellow", 0) or 0) + 2 * (own.get("red", 0) or 0),
                        "cards_against": (opp.get("yellow", 0) or 0) + 2 * (opp.get("red", 0) or 0),
                        "xg_for": own.get("xg"), "xg_against": opp.get("xg"),
                        "possession_for": own.get("possession"), "possession_against": opp.get("possession"),
                        "blocked_shots_for": own.get("blocked_shots"), "blocked_shots_against": opp.get("blocked_shots"),
                        "shots_inside_box_for": own.get("shots_inside_box"), "shots_inside_box_against": opp.get("shots_inside_box"),
                        "passes_for": own.get("passes"), "passes_against": opp.get("passes"),
                        "passes_accurate_for": own.get("passes_accurate"), "passes_accurate_against": opp.get("passes_accurate"),
                        "offsides_for": own.get("offsides"), "offsides_against": opp.get("offsides"),
                        "saves_for": own.get("saves"), "saves_against": opp.get("saves"),
                    })
                    detailed_calls += 1
                except Exception:
                    pass
            output.append(row)
        return output

    def match_context(self, fixture_id: int, deep: bool = True) -> dict[str, Any]:
        fixture = self.fixture(fixture_id)
        injuries: list[dict[str, Any]] = []
        lineups: list[dict[str, Any]] = []
        odds: list[dict[str, Any]] = []
        benchmark = None
        coverage: dict[str, Any] = {}
        current: dict[str, list[dict[str, Any]]] = {"home": [], "away": []}
        errors: list[str] = []

        try:
            if fixture.get("league_id") and fixture.get("season"):
                coverage = self.league_coverage(int(fixture["league_id"]), int(fixture["season"]))
        except Exception as exc:
            errors.append(f"coverage: {exc}")

        for label, fn in (
            ("injuries", lambda: self.injuries(fixture_id)),
            ("lineups", lambda: self.lineups(fixture_id)),
            ("odds", lambda: self.odds(fixture_id)),
            ("prediction_benchmark", lambda: self.prediction_benchmark(fixture_id)),
        ):
            try:
                value = fn()
                if label == "injuries": injuries = value
                elif label == "lineups": lineups = value
                elif label == "odds": odds = value
                else: benchmark = value
            except Exception as exc:
                errors.append(f"{label}: {exc}")

        if deep:
            for side in ("home", "away"):
                try:
                    current[side] = self.current_observations(
                        int(fixture[side]["id"]),
                        last=8,
                        max_stat_calls=6,
                        league_id=int(fixture["league_id"]) if fixture.get("league_id") else None,
                        season=int(fixture["season"]) if fixture.get("season") else None,
                    )
                except Exception as exc:
                    errors.append(f"recent_{side}: {exc}")

        return {
            "fixture": fixture,
            "injuries": injuries,
            "lineups": lineups,
            "odds": odds,
            "external_prediction_benchmark": benchmark,
            "recent_observations": current,
            "errors": errors,
            "coverage": coverage,
            "provider": self.status(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
