from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from model_buk.live_model import apply_live_model
from model_buk.multimarket import MultiMarketEngine
from model_buk.web.service import MatchAnalysisService, ServicePaths


def observations(gf=2, ga=1):
    return [{"fixture_id": i, "date": f"2026-09-{i:02d}T15:00:00+00:00", "venue": "home" if i % 2 else "away", "goals_for": gf, "goals_against": ga,
             "corners_for": 6, "corners_against": 4, "shots_for": 15, "shots_against": 10, "sot_for": 5, "sot_against": 3, "cards_for": 2, "cards_against": 3} for i in range(1, 7)]


def base():
    return {"fixture": {"date": "2026-09-20T19:00:00Z", "home_team": "UEFA New A", "away_team": "UEFA New B"}, "league": {"code": "UEL"}, "expected": {}, "factors": []}


def live():
    return {"recent_observations": {"home": observations(), "away": observations(1, 2)}}


def test_uefa_forecasts_all_observed_markets_without_domestic_archive():
    result = apply_live_model(base(), live(), pd.DataFrame())
    assert {m["group"] for m in result["markets"]} == {"goals", "result", "btts", "corners", "shots", "sot", "cards"}
    assert result["current_data"]["used_in_model"]
    assert sum(m["probability"] for m in result["markets"] if m["group"] == "result") == pytest.approx(1)
    assert all(0 < m["probability"] < 1 for m in result["markets"])
    assert all(not m["eligible_for_bet"] for m in result["markets"])


def test_missing_counts_do_not_fabricate_corner_predictions():
    data = live()
    for rows in data["recent_observations"].values():
        for row in rows:
            row["corners_for"] = row["corners_against"] = None
    result = apply_live_model(base(), data, pd.DataFrame())
    assert result["expected"]["corners"]["home"] is None
    assert not any(m["group"] == "corners" for m in result["markets"])
    assert any(m["group"] == "goals" for m in result["markets"])


def test_future_and_duplicate_observations_have_no_effect():
    data = live()
    reference = apply_live_model(base(), data, pd.DataFrame())
    data["recent_observations"]["home"] += [deepcopy(data["recent_observations"]["home"][0]), {"date": "2026-09-21T12:00:00Z", "goals_for": 100, "goals_against": 100}]
    assert apply_live_model(base(), data, pd.DataFrame())["expected"] == reference["expected"]


def test_bookmaker_prices_cannot_change_pure_probabilities():
    data = live()
    original = apply_live_model(base(), data, pd.DataFrame())["markets"]
    data['odds'] = [{'odd': 1000, 'bet_id': 5, 'value': 'Over 2.5'}]
    assert apply_live_model(base(), data, pd.DataFrame())["markets"] == original


def test_high_variance_goal_distribution_preserves_probability_mass():
    from model_buk.multimarket import MetricEstimate, _goal_special_markets, _convolved_over
    from scipy.stats import nbinom
    estimate = MetricEstimate('goals', 8, 8, .5, .5, 0, 0, 0, 0, 0, 0, 0, 0, 'test')
    rows = _goal_special_markets(estimate, 'A', 'B')
    assert sum(r['probability'] for r in rows if r['group']=='result') == pytest.approx(1)
    # Two equal negative-binomial p distributions sum to NB(r1+r2,p).
    assert _convolved_over(estimate, 20.5) == pytest.approx(nbinom.sf(20,4,.2),abs=1e-12)


def test_actual_polish_archive_missing_stats_remain_unavailable():
    engine = MultiMarketEngine(Path("data/multileague/europe16_matches_v05.csv.gz"))
    result = engine.analyze("EKSTRAKLASA", "2026-09-17", "Lech Poznan", "Legia")
    assert result["expected"]["corners"]["home"] is None
    assert not any(m["group"] == "corners" for m in result["markets"])


def test_service_uel_and_unmapped_clubs_return_shortlist(tmp_path):
    class Provider:
        connected = True
        def match_context(self, fixture_id, deep=True):
            return {**live(), "fixture": {"fixture_id": fixture_id, "league_code": "UEL", "kickoff": "2030-09-20T19:00:00Z", "home": {"id": 1, "name": "UEFA New A"}, "away": {"id": 2, "name": "UEFA New B"}}, "odds": []}
    provider = Provider()
    original = provider.match_context
    def context(*args, **kwargs):
        c = original(*args, **kwargs)
        for rows in c["recent_observations"].values():
            for row in rows:
                row["date"] = row["date"].replace("2026", "2030")
        return c
    provider.match_context = context
    paths = ServicePaths(history=tmp_path/'none', multileague_history=tmp_path/'none', model_root=tmp_path/'none', understat=tmp_path/'none', goal_model=tmp_path/'none', stadiums=tmp_path/'none')
    result = MatchAnalysisService(paths, provider).analyze_fixture(123)
    assert len(result["top_candidates"]) == 5
    assert result["most_likely"]["probability"] == max(r["probability"] for r in result["markets"])
    assert result["recommendation_summary"]["decision"] == "NO BET"
    assert len({r["group"] for r in result["top_candidates"]}) == 5
