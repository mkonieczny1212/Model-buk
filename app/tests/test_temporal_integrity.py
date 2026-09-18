import numpy as np
import pandas as pd

from model_buk.features import build_features
from model_buk.goal_engine_v06 import (
    STATE_METRICS, _append_current, _latest_league_priors,
    _poisson_market_rows, _state_at_prediction, _team_history, build_training_frame,
)


def history(n=35):
    rows = []
    for i in range(n):
        r = dict(date=pd.Timestamp("2020-01-01") + pd.Timedelta(days=i),
                 internal_match_id=i, season_id=2020, league_code="EPL", home_team="A", away_team="B")
        for side in ("home", "away"):
            for metric in ("goals", "xg", "np_xg", "ppda", "deep_completions", "expected_points",
                           "corners", "shots", "sot", "deep"):
                r[f"{side}_{metric}"] = float(i % 4 + 1)
        rows.append(r)
    return pd.DataFrame(rows)


def test_same_day_outcome_cannot_enter_corner_or_goal_features():
    raw = history()
    raw.loc[34, "date"] = raw.loc[33, "date"] + pd.Timedelta(hours=4)
    for builder in (build_features, lambda x: build_training_frame(x)[0]):
        before = builder(raw)
        changed = raw.copy()
        for col in ("home_goals", "home_xg", "home_corners", "home_shots"):
            changed.loc[33, col] = 999
        after = builder(changed)
        features = [c for c in before if c not in raw and c != "total_corners"]
        pd.testing.assert_series_equal(before.iloc[34][features], after.iloc[34][features])


def test_goal_training_and_inference_use_identical_priors_and_states():
    raw = history(765)
    raw.loc[0, "home_goals"] = 1000
    frame, _ = build_training_frame(raw)
    for index in (10, 40, 764):
        when = raw.iloc[index].date
        expected = frame.iloc[index]
        for name, value in _latest_league_priors(raw, "EPL", when).items():
            np.testing.assert_allclose(expected[name], value, equal_nan=True)
        for side, team in (("home", "A"), ("away", "B")):
            for name, value in _state_at_prediction(_team_history(raw, team), when).items():
                np.testing.assert_allclose(expected[f"{side}_{name}"], value, equal_nan=True)


def test_current_merge_preserves_process_data_normalizes_utc_and_filters_future():
    base = pd.DataFrame([{ "date": pd.Timestamp("2026-01-01 12:00"), **{m: 2. for m in STATE_METRICS}}])
    rows = [{"date": "2026-01-01T14:00:00+01:00", "goals_for": 3},
            {"date": "2026-01-02T12:00:00Z", "goals_for": 50, "xg_for": 50},
            {"date": "2026-01-03T12:00:00Z", "goals_for": 60}]
    merged = _append_current(base, rows, pd.Timestamp("2026-01-02 20:00"))
    assert len(merged) == 1
    assert merged.iloc[0].goals_for == 3
    assert merged.iloc[0].xg_for == 2
    assert merged.iloc[0].date == pd.Timestamp("2026-01-01 13:00")
    state = _state_at_prediction(merged, pd.Timestamp("2026-01-02T20:00:00Z"))
    assert state["matches_before"] == 1


def test_goals_markets_are_research_and_probability_mass_is_consistent():
    from scipy.stats import poisson
    markets = _poisson_market_rows(5.5, 0.5, "A", "B")
    probs = {m["market_key"]: m["probability"] for m in markets}
    assert np.isclose(sum(probs[k] for k in ("result.home", "result.draw", "result.away")), 1)
    assert abs(probs["goals.total.over.2.5"] - poisson.sf(2, 6.0)) < 1e-10
    assert not any(m["predictive_validated"] or m["eligible_for_bet"] for m in markets)


def test_corners_league_priors_do_not_mix_leagues():
    raw = history(50)
    raw["league_code"] = ["EPL" if i % 2 else "OTHER" for i in range(50)]
    before = build_features(raw)
    raw.loc[raw.league_code.eq("OTHER"), "home_corners"] = 1000
    after = build_features(raw)
    assert before.iloc[-1].league_home_corners_r100 == after.iloc[-1].league_home_corners_r100
