from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from model_buk.config import CornerV02Config, load_corner_v02_config
from model_buk.data_readiness import readiness_summary
from model_buk.inference import attach_total_market_price
from model_buk.goal_engine_v06 import DynamicGoalEngineV06, load_understat
from model_buk.live_adjustment import apply_current_observations
from model_buk.live_model import apply_live_model
from model_buk.security import safe_error
from model_buk.live_provider import ApiFootballClient
from model_buk.multimarket import MultiMarketEngine, rebuild_markets_from_expected
from model_buk.catalog import LEAGUES
from model_buk.odds_parser import normalize_odds, rank_opportunities
from model_buk.strategy import DEFAULT_STRATEGY, StrategyProfile, build_strategy_scan
from model_buk.suite import LiveCornerSuite, load_live_corner_suite, predict_with_live_suite
from model_buk.weather import weather_context


@dataclass(frozen=True)
class ServicePaths:
    history: Path = Path("data/canonical/epl_matches_v01.csv.gz")
    model_root: Path = Path("models")
    config: Path = Path("config/corners_v02.toml")
    multileague_history: Path = Path("data/multileague/europe16_matches_v05.csv.gz")
    stadiums: Path = Path("data/stadiums_europe.json")
    understat: Path = Path("data/understat")
    goal_model: Path = Path("models/goal_v06")


class PredictionService:
    """Backward-compatible service around the frozen EPL corner suite."""

    def __init__(self, paths: ServicePaths | None = None):
        self.paths = paths or ServicePaths()
        self._history: pd.DataFrame | None = None
        self._suite: LiveCornerSuite | None = None
        self._cfg: CornerV02Config | None = None

    @property
    def cfg(self) -> CornerV02Config:
        if self._cfg is None:
            self._cfg = load_corner_v02_config(self.paths.config)
        return self._cfg

    @property
    def history(self) -> pd.DataFrame:
        if self._history is None:
            frame = pd.read_csv(self.paths.history)
            frame["date"] = pd.to_datetime(frame["date"], format="mixed")
            self._history = frame
        return self._history

    @property
    def suite(self) -> LiveCornerSuite:
        if self._suite is None:
            self._suite = load_live_corner_suite(self.paths.model_root)
        return self._suite

    def teams(self) -> list[str]:
        frame = self.history
        teams = set(frame["home_team"].dropna().astype(str)) | set(frame["away_team"].dropna().astype(str))
        return sorted(teams)

    def status(self) -> dict[str, Any]:
        history = self.history
        latest = pd.Timestamp(history["date"].max())
        now = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)
        latest_naive = latest.tz_localize(None) if latest.tzinfo else latest
        stale_days = max(0, int((now - latest_naive).total_seconds() // 86400))
        return {
            "status": "ok",
            "deployment_status": self.suite.registry.get("deployment_status", "research/paper only"),
            "history_rows": int(len(history)),
            "history_from": str(history["date"].min()),
            "history_through": str(latest),
            "data_staleness_days": stale_days,
            "total_model": self.suite.total_metadata.get("model_version"),
            "team_model": self.suite.team_engine.metadata.get("version"),
            "registry_as_of": self.suite.registry.get("as_of"),
        }

    def predict(self, *, date: str, home_team: str, away_team: str, line: float | None = None, over_odds: float | None = None, under_odds: float | None = None) -> dict[str, Any]:
        known_teams = set(self.teams())
        if home_team not in known_teams:
            raise ValueError(f"Unknown home team: {home_team}")
        if away_team not in known_teams:
            raise ValueError(f"Unknown away team: {away_team}")
        if home_team == away_team:
            raise ValueError("home_team and away_team must differ")
        supplied = [x is not None for x in (line, over_odds, under_odds)]
        if any(supplied) and not all(supplied):
            raise ValueError("line, over_odds and under_odds must be supplied together")
        prediction = predict_with_live_suite(self.history, self.suite, self.cfg, date=date, home_team=home_team, away_team=away_team)
        prediction["generated_at"] = datetime.now(timezone.utc).isoformat()
        prediction["data_status"] = self.status()
        if all(supplied):
            stub = {"total_markets": prediction["total_corners"]["markets"]}
            priced = attach_total_market_price(stub, self.cfg, line=float(line), over_odds=float(over_odds), under_odds=float(under_odds))
            prediction["market_check"] = priced["market_check"]
        return prediction


class MatchAnalysisService:
    """v0.6 orchestration: many leagues, many markets, current context and odds."""

    def __init__(self, paths: ServicePaths | None = None, provider: ApiFootballClient | None = None):
        self.paths = paths or ServicePaths()
        self.multimarket = MultiMarketEngine(self.paths.multileague_history)
        self.provider = provider or ApiFootballClient()
        self.corner_service: PredictionService | None = None
        self.goal_engine: DynamicGoalEngineV06 | None = None
        self.model_loading_errors: list[dict[str, str]] = []
        self.strategy = DEFAULT_STRATEGY
        self.understat_history = pd.DataFrame()
        if self.paths.understat.exists():
            try:
                self.understat_history = load_understat(self.paths.understat)
            except Exception as exc:
                self.model_loading_errors.append({"component": "Understat", "error_type": type(exc).__name__, "reason": "Nie udało się odczytać danych Understat."})
        try:
            if self.paths.history.exists() and self.paths.model_root.exists():
                self.corner_service = PredictionService(self.paths)
        except Exception:
            self.corner_service = None
        try:
            if self.paths.understat.exists() and self.paths.goal_model.exists():
                self.goal_engine = DynamicGoalEngineV06(self.paths.understat, self.paths.goal_model)
        except Exception as exc:
            self.goal_engine = None
            self.model_loading_errors.append({"component": "goal_v06", "error_type": type(exc).__name__, "reason": "Nie załadowano modelu xG. Sprawdź artefakty i requirements-lock.txt; silnik live działa niezależnie."})

    def status(self) -> dict[str, Any]:
        leagues = self.multimarket.leagues()
        latest = max((x["history_through"] for x in leagues if x["history_through"]), default=None)
        return {
            "status": "ok" if (self.provider.connected or not self.multimarket.history.empty) and not self.model_loading_errors else "degraded",
            "app_version": "0.9.0",
            "deployment_status": "research / paper betting",
            "live_provider": self.provider.status(),
            "leagues": len(leagues),
            "historical_matches": int(sum(x["matches"] for x in leagues)),
            "history_through": latest,
            "market_engines": ["1X2", "BTTS", "Goals", "Corners", "Shots", "SOT", "Cards"],
            "goal_dynamic_xg_available": self.goal_engine is not None,
            "model_loading_errors": self.model_loading_errors,
            "understat_matches": len(self.understat_history),
            "understat_through": str(self.understat_history.date.max()) if not self.understat_history.empty else None,
            "goal_dynamic_xg_leagues": sorted(self.goal_engine.supported_leagues) if self.goal_engine else [],
            "epl_corner_champion_available": self.corner_service is not None,
            "pure_model_rule": "Bookmaker odds are never model inputs; prices are attached only after PURE probabilities exist.",
            "data_policy": "If a feature is not historically trainable and OOS-tested, it is shown as context/quality gate rather than given an invented probability weight.",
            "data_readiness": readiness_summary(),
            "team_catalog_source": "API-Football current season" if self.provider.connected else "local historical fallback",
            "strategy": self.strategy.to_dict(),
            "validation": {
                "mode": "prospective_closed_loop",
                "promotion_gate": "n>=200, ROI lower 95% > 0, CLV lower 95% > 0, ECE <= 5pp",
                "automatic_maintenance": True,
            },
        }

    def leagues(self) -> list[dict[str, Any]]:
        return self.multimarket.leagues()

    def teams(self, league_code: str) -> list[str]:
        # With a connected live provider the selector must reflect the CURRENT
        # competition roster, not every club that happened to appear in history.
        if self.provider.connected:
            try:
                return [row["name"] for row in self.provider.teams_for_league(league_code)]
            except Exception:
                # Keep the manual tool usable if the provider is temporarily
                # unavailable, but never use this fallback for live fixture IDs.
                pass
        return self.multimarket.teams(league_code)

    def fixtures(self, date: str, league_codes: list[str] | None = None) -> dict[str, Any]:
        if not self.provider.connected:
            return {
                "mode": "manual",
                "fixtures": [],
                "message": "Podłącz API-Football, aby aplikacja sama pobierała bieżące mecze. Analiza ręczna wielu lig działa bez API.",
                "provider": self.provider.status(),
            }
        return {
            "mode": "live",
            "fixtures": self.provider.fixtures(date, league_codes),
            "provider": self.provider.status(),
        }

    @staticmethod
    def _corner_reference_to_markets(reference: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for m in reference.get("total_corners", {}).get("markets", []):
            line = float(m["line"])
            rows.append({"market_key": f"corners.total.over.{line}", "label": f"Powyżej {line}", "group": "corners", "threshold": line, "side": "over", "probability": float(m["p_over"]), "fair_odds": float(m["fair_over"])})
            rows.append({"market_key": f"corners.total.under.{line}", "label": f"Poniżej {line}", "group": "corners", "threshold": line, "side": "under", "probability": float(m["p_under"]), "fair_odds": float(m["fair_under"])})
        for m in reference.get("team_corners", {}).get("markets", []):
            line = float(m["line"]); side = m["side"]
            rows.append({"market_key": f"corners.{side}.over.{line}", "label": f"{m['team']}: powyżej {line}", "group": "corners", "threshold": line, "side": "over", "probability": float(m["p_over"]), "fair_odds": float(m["fair_over"])})
            rows.append({"market_key": f"corners.{side}.under.{line}", "label": f"{m['team']}: poniżej {line}", "group": "corners", "threshold": line, "side": "under", "probability": float(m["p_under"]), "fair_odds": float(m["fair_under"])})
        return rows

    def _attach_epl_corner_reference(self, analysis: dict[str, Any]) -> None:
        if analysis["league"]["code"] != "EPL" or self.corner_service is None:
            return
        h = analysis["fixture"]["home_team"]
        a = analysis["fixture"]["away_team"]
        try:
            # Resolve names against the canonical EPL model history.
            candidates = self.corner_service.teams()
            from model_buk.team_names import resolve_team_name
            rh, _ = resolve_team_name(h, candidates); ra, _ = resolve_team_name(a, candidates)
            if not rh or not ra:
                return
            ref = self.corner_service.predict(date=analysis["fixture"]["date"], home_team=rh, away_team=ra)
            analysis["benchmarks"] = analysis.get("benchmarks", {})
            analysis["benchmarks"]["epl_corner_champion"] = {
                "status": "legacy_reference_requires_retraining",
                "model": ref.get("total_corners", {}).get("model"),
                "expected_total": ref.get("total_corners", {}).get("expected_total"),
                "expected_home": ref.get("team_corners", {}).get("expected_home"),
                "expected_away": ref.get("team_corners", {}).get("expected_away"),
                "markets": self._corner_reference_to_markets(ref),
                "note": "Legacy EPL corner reference. Its artifacts predate the corrected temporal feature policy and require retraining; not a validated current prediction.",
            }
        except Exception as exc:
            analysis.setdefault("warnings", []).append(f"EPL corner benchmark unavailable: {safe_error(exc)}")

    def _apply_goal_v06(self, analysis: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
        if self.goal_engine is None:
            analysis.setdefault("warnings", []).append("Dynamic xG goal engine is unavailable.")
            return analysis
        league_code = analysis["league"]["code"]
        if league_code not in self.goal_engine.supported_leagues:
            analysis.setdefault("model_readiness", {})["goals"] = {
                "grade": "B",
                "eligible_for_bet": False,
                "reason": "No uniform historical xG/process training set for this league yet.",
            }
            return analysis
        observations = live.get("recent_observations") or {}
        try:
            pred = self.goal_engine.predict(
                league_code=league_code,
                when=analysis["fixture"]["date"],
                home_name=analysis["fixture"].get("provider_home", {}).get("name") or analysis["fixture"]["home_team"],
                away_name=analysis["fixture"].get("provider_away", {}).get("name") or analysis["fixture"]["away_team"],
                home_current=observations.get("home") or [],
                away_current=observations.get("away") or [],
            )
        except Exception as exc:
            analysis.setdefault("warnings", []).append(f"Dynamic goal engine unavailable for this fixture: {safe_error(exc)}")
            return analysis

        # Replace only goal-derived markets. Other event markets keep their own engine/status.
        keep = [m for m in analysis.get("markets", []) if m.get("group") not in {"result", "btts", "goals"}]
        analysis["markets"] = pred["markets"] + keep
        analysis["expected"]["goals"] = {
            "home": pred["lambda_home"], "away": pred["lambda_away"],
            "total": round(pred["lambda_home"] + pred["lambda_away"], 4),
            "source": pred["engine_version"],
        }
        analysis.setdefault("model_readiness", {})["goals"] = {
            "grade": "RESEARCH",
            "predictive_validated": False,
            "market_validated": False,
            "eligible_for_bet": False,
            "reason": "Corrected research model: current-provider calibration and prospective validation remain required.",
            "engine": pred["engine_version"],
            "feature_coverage": pred["feature_coverage"],
            "current_xg_observations": pred["current_xg_observations"],
            "training": pred.get("training"),
        }
        analysis.setdefault("factors", []).append({
            "key": "goal_dynamic_xg_v06",
            "label": "Dynamiczny stan xG / proces gry",
            "home": {"lambda": pred["lambda_home"], "mapped_team": pred["understat_home"]},
            "away": {"lambda": pred["lambda_away"], "mapped_team": pred["understat_away"]},
            "status": "model_input",
            "explanation": "OOS-trained Poisson-loss model on point-in-time xG/npxG/PPDA/deep-completions states, rest/congestion and learned interactions. Current API xG extends the state only when provider returns it.",
        })
        return analysis

    @staticmethod
    def _context_cards(live: dict[str, Any], weather: dict[str, Any] | None) -> list[dict[str, Any]]:
        fixture = live.get("fixture") or {}
        injuries = live.get("injuries") or []
        lineups = live.get("lineups") or []
        home_id = (fixture.get("home") or {}).get("id")
        away_id = (fixture.get("away") or {}).get("id")
        home_inj = [x for x in injuries if x.get("team_id") == home_id]
        away_inj = [x for x in injuries if x.get("team_id") == away_id]
        cards = [
            {
                "key": "injuries",
                "label": "Kontuzje / zawieszenia",
                "home": len(home_inj),
                "away": len(away_inj),
                "details": {"home": home_inj, "away": away_inj},
                "status": "quality_gate",
                "model_usage": "not_probability_input_yet",
                "explanation": "Aktualne absencje są pobierane, ale bez player-strength nie dostają arbitralnej wagi w probability.",
            },
            {
                "key": "lineups",
                "label": "Składy",
                "home": next((x for x in lineups if x.get("team_id") == home_id), None),
                "away": next((x for x in lineups if x.get("team_id") == away_id), None),
                "status": "confirmed" if len(lineups) >= 2 else "not_confirmed",
                "model_usage": "quality_gate",
                "explanation": "Potwierdzone XI jest kontekstem. Wpływ zmian składu wymaga osobnego modelu i walidacji.",
            },
            {
                "key": "referee",
                "label": "Sędzia",
                "value": fixture.get("referee"),
                "status": "context",
                "model_usage": "monitor_only",
                "explanation": "Nie wpływa na probability, dopóki referee×team interaction nie przejdzie testu OOS.",
            },
            {
                "key": "venue",
                "label": "Stadion",
                "value": fixture.get("venue"),
                "status": "context",
                "model_usage": "venue_home_away_already_in_model",
            },
        ]
        if weather:
            cards.append({
                "key": "weather",
                "label": "Pogoda",
                "value": weather,
                "status": "context",
                "model_usage": weather.get("model_usage", "monitor_only"),
                "explanation": weather.get("note"),
            })
        return cards

    @staticmethod
    def _model_only_candidates(markets: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
        """Readable fallback when the odds feed has no comparable price.

        These are model forecasts, NOT value bets. We deliberately diversify by
        market family so the UI does not show five near-identical complements of
        the same line.
        """
        valid = [r for r in markets if r.get("probability") is not None]
        ranked = sorted(valid, key=lambda r: float(r["probability"]), reverse=True)
        selected, groups = [], set()
        for row in ranked:
            if row.get("group") in groups:
                continue
            groups.add(row.get("group"))
            selected.append({**row, "bookmaker": None, "odds": None,
                             "market_probability": None, "edge": None, "ev": None,
                             "decision": "NO BET", "decision_reason": "Brak aktualnego porównywalnego kursu; to prognoza prawdopodobieństwa."})
            if len(selected) >= limit:
                break
        return selected

    def analyze_manual(self, league_code: str, date: str, home_team: str, away_team: str, persist_context: bool = False) -> dict[str, Any]:
        analysis = self.multimarket.analyze(league_code, date, home_team, away_team)
        analysis["mode"] = "manual_historical_baseline"
        analysis["current_context"] = {
            "connected": False,
            "message": "To jest szeroki baseline. Aby użyć bieżących meczów, kontuzji, lineupów i kursów, podłącz API-Football lub analizuj fixture z dashboardu.",
        }
        analysis = self._apply_goal_v06(analysis, {"recent_observations": {"home": [], "away": []}})
        analysis.setdefault("model_readiness", {}).setdefault("corners", {"grade": "B", "eligible_for_bet": False, "reason": "Current corner model is still a benchmark; richer style/lineup training is pending."})
        analysis["model_readiness"].setdefault("shots", {"grade": "B", "eligible_for_bet": False, "reason": "Historical price validation is incomplete."})
        analysis["model_readiness"].setdefault("sot", {"grade": "B", "eligible_for_bet": False, "reason": "Historical SOT price validation is incomplete."})
        analysis["model_readiness"].setdefault("cards", {"grade": "B", "eligible_for_bet": False, "reason": "Referee/player interactions are not trained OOS yet."})
        self._attach_epl_corner_reference(analysis)
        analysis["opportunities"] = []
        analysis["market_comparison"] = []
        analysis["top_candidates"] = self._model_only_candidates(analysis.get("markets", []), limit=5)
        analysis["top_candidates_mode"] = "model_only_manual"
        analysis["generated_at"] = datetime.now(timezone.utc).isoformat()
        return analysis

    def _context_only_analysis(self, fixture: dict[str, Any]) -> dict[str, Any]:
        code = fixture.get("league_code")
        spec = LEAGUES.get(code)
        return {
            "engine_version": "context-only-v0.6",
            "league": {"code": code, "name": spec.name if spec else fixture.get("league_name"), "country": spec.country if spec else fixture.get("country")},
            "fixture": {
                "date": fixture.get("kickoff"), "home_team": (fixture.get("home") or {}).get("name"),
                "away_team": (fixture.get("away") or {}).get("name"), "round": fixture.get("round"),
                "fixture_id": fixture.get("fixture_id"), "provider_home": fixture.get("home"),
                "provider_away": fixture.get("away"), "venue": fixture.get("venue"), "referee": fixture.get("referee"),
            },
            "expected": {m: {"home": None, "away": None, "total": None, "source": "not_ready"} for m in ("goals", "corners", "shots", "sot", "cards")},
            "markets": [], "factors": [], "data_quality": {
                "score": 25,
                "warning": "NO PREDICTION: competition-specific historical feature store is not ready. Current context is shown without inventing probabilities.",
            },
            "model_readiness": {
                "goals": {"grade": "LIVE", "eligible_for_bet": False, "reason": "UEFA historical feature backfill not integrated yet."},
                "corners": {"grade": "LIVE", "eligible_for_bet": False, "reason": "UEFA historical feature backfill not integrated yet."},
                "shots": {"grade": "LIVE", "eligible_for_bet": False, "reason": "UEFA historical feature backfill not integrated yet."},
                "sot": {"grade": "LIVE", "eligible_for_bet": False, "reason": "UEFA historical feature backfill not integrated yet."},
                "cards": {"grade": "LIVE", "eligible_for_bet": False, "reason": "UEFA historical feature backfill not integrated yet."},
            },
        }

    def analyze_fixture(self, fixture_id: int, deep: bool = True) -> dict[str, Any]:
        if not self.provider.connected:
            raise RuntimeError("API-Football nie jest podłączone.")
        live = self.provider.match_context(fixture_id, deep=deep)
        fixture = live["fixture"]
        league_code = fixture.get("league_code")
        if not league_code:
            raise ValueError(f"Liga fixture_id={fixture_id} nie jest jeszcze wspierana przez v0.6")

        # Competition membership never blocks probability calculation: derive
        # each market from available completed matches for the two real teams.
        analysis = self._context_only_analysis(fixture)
        analysis = apply_live_model(analysis, live, self.multimarket.history, self.understat_history)
        analysis.setdefault("warnings", []).extend(x["reason"] for x in self.model_loading_errors)
        # Keep the learned xG model as an independent challenger until the
        # provider shift and new live pipeline have been evaluated together.
        if self.goal_engine is not None and league_code in self.goal_engine.supported_leagues:
            try:
                observations = live.get("recent_observations") or {}
                pred = self.goal_engine.predict(league_code, fixture["kickoff"], fixture["home"]["name"], fixture["away"]["name"],
                                                home_current=observations.get("home") or [], away_current=observations.get("away") or [])
                analysis.setdefault("benchmarks", {})["dynamic_xg"] = pred
                analysis["factors"].append({"key": "dynamic_xg_challenger", "label": "Wyuczony model xG — porównanie", "home": pred["lambda_home"], "away": pred["lambda_away"], "status": "context", "explanation": "Oddzielna prognoza wyuczonego modelu. Różnic względem modelu live nie maskujemy arbitralną średnią."})
            except Exception as exc:
                analysis.setdefault("warnings", []).append("Model porównawczy xG niedostępny: " + safe_error(exc))
        analysis["mode"] = "live_current_context"

        weather = None
        if self.paths.stadiums.exists():
            try:
                weather = weather_context(self.paths.stadiums, fixture)
            except Exception as exc:
                weather = {"available": False, "reason": safe_error(exc)}
        analysis["factors"] = analysis.get("factors", []) + self._context_cards(live, weather)
        analysis["current_context"] = {
            "connected": True,
            "provider": live.get("provider"),
            "injuries": live.get("injuries"),
            "lineups": live.get("lineups"),
            "weather": weather,
            "external_prediction_benchmark": live.get("external_prediction_benchmark"),
            "coverage": live.get("coverage") or {},
            "errors": live.get("errors"),
        }

        analysis.setdefault("model_readiness", {}).setdefault("corners", {"grade": "B", "eligible_for_bet": False, "reason": "Current-context corner model still lacks a unified xG/style/lineup historical training layer."})
        analysis["model_readiness"].setdefault("shots", {"grade": "B", "eligible_for_bet": False, "reason": "Predictive count baseline only; historical price validation for team/player shot props is incomplete."})
        analysis["model_readiness"].setdefault("sot", {"grade": "B", "eligible_for_bet": False, "reason": "Predictive count baseline only; historical SOT price validation is incomplete."})
        analysis["model_readiness"].setdefault("cards", {"grade": "B", "eligible_for_bet": False, "reason": "Referee and lineup interactions are not yet trained OOS."})

        raw_odds = live.get("odds") or []
        opportunities, compared = rank_opportunities(
            analysis["markets"],
            raw_odds,
            min_edge=self.strategy.min_conservative_edge,
            min_ev=self.strategy.min_conservative_net_ev,
            prefer_polish=False,
            max_odds_age_hours=self.strategy.max_odds_age_hours,
            stake_cost_rate=self.strategy.stake_tax_rate,
            winnings_cost_rate=self.strategy.winnings_cost_rate,
            min_odds=self.strategy.min_odds,
            max_odds=self.strategy.max_odds,
            fallback_probability_haircut=self.strategy.fallback_probability_haircut,
            require_interval_for_bet=self.strategy.require_validated_interval_for_bet,
            keep_all_bookmakers=True,
        )
        if self.strategy.mode == "PAPER":
            for row in compared:
                if row.get("decision") == "BET":
                    row["decision"] = "PAPER"
                    row["decision_reason"] = (
                        "Kandydat spełnia progi ceny i wartości, ale aktywny profil "
                        "działa w trybie PAPER do zakończenia walidacji prospektywnej."
                    )
            opportunities = []
        analysis["opportunities"] = opportunities[:12]
        analysis["market_comparison"] = compared
        by_key: dict[str, dict[str, Any]] = {}
        for row in compared:
            by_key.setdefault(str(row["market_key"]), row)
        candidates = self._model_only_candidates(analysis["markets"], limit=5)
        best = max(analysis["markets"], key=lambda r: r["probability"], default=None)
        analysis["most_likely"] = by_key.get(best["market_key"], next((r for r in candidates if r["market_key"] == best["market_key"]), best)) if best else None
        analysis["recommendation_summary"] = {"decision": "BET" if opportunities else "NO BET", "bet_count": len(opportunities),
                                               "reason": "Dostępne zakłady przeszły kontrolę kursu, walidacji i wartości." if opportunities else "Prognozy są dostępne, ale żaden zakład nie przeszedł wszystkich kontroli ceny i walidacji."}
        analysis["raw_odds_count"] = len(raw_odds)
        analysis["normalized_odds"] = normalize_odds(raw_odds)

        self._attach_epl_corner_reference(analysis)

        analysis["confidence"] = {"score": analysis["data_quality"]["score"], "label": "pokrycie danych, nie pewność trafienia", "calibrated": False}
        analysis["prediction_scope"] = "prematch_90_minutes"
        analysis["prospective"] = pd.Timestamp(fixture["kickoff"]) > pd.Timestamp.now(tz="UTC")
        analysis["generated_at"] = datetime.now(timezone.utc).isoformat()
        strategy_scan = build_strategy_scan([analysis], self.strategy)
        strategy_candidates = strategy_scan["singles"]
        if strategy_candidates:
            analysis["top_candidates"] = strategy_candidates
            analysis["top_candidates_mode"] = "paper_value_strategy"
            analysis["recommendation_summary"] = {
                "decision": strategy_candidates[0]["strategy_decision"],
                "bet_count": len(opportunities),
                "paper_count": len(strategy_candidates),
                "reason": "Najlepsza propozycja przeszła profil wartości 1,50–1,90. Pozostaje PAPER do walidacji prospektywnej.",
            }
        else:
            analysis["top_candidates"] = [by_key.get(r["market_key"], r) for r in candidates]
            analysis["top_candidates_mode"] = "highest_probability_diversified"
        analysis["strategy"] = strategy_scan
        return analysis

    def scan_fixtures(
        self,
        date: str,
        league_codes: list[str] | None = None,
        *,
        max_fixtures: int = 5,
        deep: bool = False,
        profile: StrategyProfile | None = None,
    ) -> dict[str, Any]:
        profile = profile or self.strategy
        listing = self.fixtures(date, league_codes)
        now = datetime.now(timezone.utc)
        all_fixtures = listing.get("fixtures") or []
        prospective_fixtures: list[dict[str, Any]] = []
        for fixture in all_fixtures:
            try:
                kickoff = datetime.fromisoformat(str(fixture.get("kickoff")).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            if kickoff > now and str(fixture.get("status") or "").upper() in {"NS", "TBD", "PST"}:
                prospective_fixtures.append(fixture)
        fixtures = prospective_fixtures[: max(1, min(int(max_fixtures), 10))]
        analyses: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for fixture in fixtures:
            fixture_id = fixture.get("fixture_id")
            try:
                analyses.append(self.analyze_fixture(int(fixture_id), deep=deep))
            except Exception as exc:
                errors.append(
                    {
                        "fixture_id": fixture_id,
                        "home_team": (fixture.get("home") or {}).get("name"),
                        "away_team": (fixture.get("away") or {}).get("name"),
                        "reason": safe_error(exc),
                    }
                )
        result = build_strategy_scan(analyses, profile, errors=errors)
        result.update(
            {
                "target_date": date,
                "fixture_mode": listing.get("mode"),
                "provider_message": listing.get("message"),
                "requested_fixture_count": len(fixtures),
                "skipped_non_prospective_count": len(all_fixtures) - len(prospective_fixtures),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed_with_errors" if errors else "completed",
            }
        )
        return result

