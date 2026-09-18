from datetime import datetime, timezone

import pytest

from model_buk.odds_parser import normalize_odds, rank_opportunities


NOW = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)


def priced(market=None, odd=None, **kwargs):
    model = {"market_key": "goals.total.over.2.5", "probability": .8,
             "eligible_for_bet": True, "predictive_validated": True, **(market or {})}
    quote = {"bookmaker": "Test", "bet_id": 5, "value": "Over 2.5",
             "odd": 2.0, "update": NOW.isoformat(), **(odd or {})}
    return rank_opportunities([model], [quote], now=NOW, **kwargs)


def test_bet_requires_validation_freshness_and_conservative_value():
    assert priced()[0]
    for market, quote in [({"predictive_validated": False}, {}),
                          ({"eligible_for_bet": False}, {}),
                          ({}, {"update": "2026-09-15T12:00:00Z"}),
                          ({}, {"update": "2026-09-17T12:00:00Z"}),
                          ({}, {"update": None}),
                          ({}, {"update": "2026-09-16T12:00:00"}),
                          ({"probability_interval": [.4, .9]}, {})]:
        bets, rows = priced(market, quote)
        assert not bets
        assert rows[0]["decision"] == "NO BET"
        assert rows[0]["decision_reason"]
        assert rows[0]["probability"] == .8


@pytest.mark.parametrize("value", [None, "x", 0, 1, -1, float("nan"), float("inf")])
def test_invalid_prices_do_not_crash_or_produce_opportunities(value):
    assert priced(odd={"odd": value}) == ([], [])


def test_cards_require_matching_settlement():
    market = {"market_key": "cards.total.over.2.5", "settlement_rule": "yellow_plus_two_red"}
    quote = {"bet_id": 80}
    assert not priced(market, quote)[0]
    assert priced(market, {**quote, "settlement_rule": "yellow_plus_two_red"})[0]


def test_costs_are_explicit_and_can_remove_positive_value():
    bets, rows = priced(stake_cost_rate=.4)
    assert not bets
    assert rows[0]["ev"] > 0
    assert rows[0]["net_ev"] < 0
    assert rows[0]["cost_assumptions"]["stake_cost_rate"] == .4


def test_persist_false_does_not_save_prediction_or_odds():
    from fastapi.testclient import TestClient
    from model_buk.web.api import create_app

    class Service:
        def status(self):
            return {"status": "degraded"}

        def analyze_fixture(self, fixture_id, deep=True):
            return {"normalized_odds": [{"odd": 2.0}]}

        def fixtures(self, *args):
            raise AssertionError("Empty selection must not fetch fixtures")

    class Store:
        def save(self, *args):
            raise AssertionError("Unexpected prediction write")

        def save_odds(self, *args):
            raise AssertionError("Unexpected odds write")

    client = TestClient(create_app(service=Service(), analysis_service=Service(), store=Store()))
    response = client.post('/api/analyze/fixture/1?persist=false')
    assert response.status_code == 200
    assert "prediction_id" not in response.json()
    assert client.get('/api/health').json() == {"status": "degraded"}
    assert client.get('/api/fixtures?date=2026-09-16&league=').json()["fixtures"] == []


def test_provider_exception_does_not_escape_api():
    from fastapi.testclient import TestClient
    from model_buk.web.api import create_app

    class Broken:
        def analyze_fixture(self, *args, **kwargs):
            raise RuntimeError("https://provider.test?key=do-not-expose-this")

    response = TestClient(create_app(service=Broken(), analysis_service=Broken(), store=object())).post('/api/analyze/fixture/1?persist=false')
    assert response.status_code == 503
    assert "do-not-expose-this" not in response.text
