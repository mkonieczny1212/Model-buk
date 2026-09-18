from pathlib import Path

from model_buk.goal_engine_v06 import DynamicGoalEngineV06, load_understat
from model_buk.data_readiness import readiness_summary


def test_understat_bundle_is_big_five_and_not_tiny():
    frame = load_understat(Path("data/understat"))
    assert len(frame) >= 21789
    assert frame[frame.season_id.eq(2021)].league_code.nunique() == 5
    assert frame[frame.season_id.eq(2026)].league_code.nunique() == 5
    assert not frame.game_id.duplicated().any()
    assert set(frame.league_code.unique()) == {"EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"}
    assert str(frame.date.max().date()) >= "2026-05-01"


def test_dynamic_goal_engine_returns_valid_market_distribution():
    engine = DynamicGoalEngineV06(Path("data/understat"), Path("models/goal_v06"))
    pred = engine.predict("EPL", "2026-09-15T20:00:00", "Arsenal", "Chelsea")
    assert pred["engine_version"] == "goal-dynamic-xg-v0.6"
    assert pred["lambda_home"] > 0
    assert pred["lambda_away"] > 0
    result_rows = [m for m in pred["markets"] if m["group"] == "result"]
    assert abs(sum(m["probability"] for m in result_rows) - 1.0) < 1e-6
    assert not any(m["predictive_validated"] for m in pred["markets"])
    assert pred["validation_status"] == "research_only"
    assert not any(m["eligible_for_bet"] for m in pred["markets"])


def test_data_readiness_does_not_claim_full_coverage():
    r = readiness_summary()
    assert r["complete_for_full_target_model"] is False
    assert r["critical_gaps"]
