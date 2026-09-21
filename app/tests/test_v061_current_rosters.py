from pathlib import Path

from model_buk.goal_engine_v06 import DynamicGoalEngineV06
from model_buk.team_names import resolve_team_name
from model_buk.web.service import MatchAnalysisService, ServicePaths
from model_buk.web.service_v062 import MatchAnalysisService as DecoratedMatchAnalysisService


def test_cross_provider_athletic_bilbao_resolves_to_understat():
    name, score = resolve_team_name("Athletic Bilbao", ["Athletic Club", "Levante", "Barcelona"])
    assert name == "Athletic Club"
    assert score == 1.0


def test_dynamic_goal_engine_can_price_levante_athletic_bilbao():
    engine = DynamicGoalEngineV06(Path("data/understat"), Path("models/goal_v06"))
    pred = engine.predict("LALIGA", "2026-09-16T19:30:00", "Levante", "Athletic Bilbao")
    assert pred["understat_home"] == "Levante"
    assert pred["understat_away"] == "Athletic Club"
    assert pred["markets"]
    assert pred["lambda_home"] > 0
    assert pred["lambda_away"] > 0


class CurrentRosterProvider:
    connected = True

    def status(self):
        return {"name": "fake", "connected": True}

    def teams_for_league(self, league_code):
        assert league_code == "EKSTRAKLASA"
        return [
            {"id": 1, "name": "Lech Poznan", "season": 2026},
            {"id": 2, "name": "Legia Warszawa", "season": 2026},
        ]


def test_team_selector_prefers_current_provider_roster(tmp_path: Path):
    paths = ServicePaths(
        history=Path("does-not-exist.csv"),
        model_root=tmp_path / "models-none",
        config=Path("config/corners_v02.toml"),
        multileague_history=Path("data/multileague/europe16_matches_v05.csv.gz"),
        stadiums=Path("does-not-exist.json"),
    )
    service = MatchAnalysisService(paths=paths, provider=CurrentRosterProvider())
    assert service.teams("EKSTRAKLASA") == ["Lech Poznan", "Legia Warszawa"]


def test_decorated_service_falls_back_to_historical_teams_when_roster_plan_fails(tmp_path: Path):
    class RestrictedProvider(CurrentRosterProvider):
        def teams_for_league(self, league_code):
            raise RuntimeError("plan")

    paths = ServicePaths(
        history=Path("does-not-exist.csv"),
        model_root=tmp_path / "models-none",
        config=Path("config/corners_v02.toml"),
        multileague_history=Path("data/multileague/europe16_matches_v05.csv.gz"),
        stadiums=Path("does-not-exist.json"),
        understat=Path("does-not-exist-understat"),
        goal_model=Path("does-not-exist-goals"),
    )
    service = DecoratedMatchAnalysisService(paths=paths, provider=RestrictedProvider())
    teams = service.teams("LALIGA")
    assert "Barcelona" in teams
    assert len(teams) > 2


def test_model_only_shortlist_is_not_blank_without_odds():
    markets = [
        {"market_key": "result.home", "label": "Home", "group": "result", "probability": 0.61, "fair_odds": 1.64, "model_grade": "A"},
        {"market_key": "goals.total.over.2.5", "label": "O2.5", "group": "goals", "probability": 0.58, "fair_odds": 1.72, "model_grade": "A"},
        {"market_key": "btts.yes", "label": "BTTS", "group": "btts", "probability": 0.56, "fair_odds": 1.79, "model_grade": "A"},
    ]
    rows = MatchAnalysisService._model_only_candidates(markets, limit=5)
    assert len(rows) == 3
    assert all(r["decision"] == "NO BET" for r in rows)

