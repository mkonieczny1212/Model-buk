from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from model_buk.settlement import SettlementEngine, clv, selection_returns, settle_market, validation_report
from model_buk.strategy import DEFAULT_STRATEGY
from model_buk.web.api import create_app
from model_buk.web.storage import PredictionStore


FIXTURE = {
    "status": "FT",
    "home": {"id": 10, "name": "Home", "goals": 2},
    "away": {"id": 20, "name": "Away", "goals": 1},
}
STATS = {
    10: {"corners": 7, "shots": 13, "sot": 5, "yellow": 2, "red": 1},
    20: {"corners": 3, "shots": 8, "sot": 3, "yellow": 1, "red": 0},
}


@pytest.mark.parametrize(
    ("market", "result"),
    [
        ("result.home", "WON"),
        ("result.draw", "LOST"),
        ("btts.yes", "WON"),
        ("goals.total.over.2.5", "WON"),
        ("goals.home.under.2.5", "WON"),
        ("corners.total.over.9.5", "WON"),
        ("shots.away.under.8.5", "WON"),
        ("sot.total.under.8.5", "WON"),
        ("cards.total.over.4.5", "WON"),
    ],
)
def test_supported_markets_are_settled(market: str, result: str) -> None:
    assert settle_market(market, FIXTURE, STATS)["result"] == result


def test_integer_line_push_and_missing_statistics_are_explicit() -> None:
    assert settle_market("corners.total.over.10", FIXTURE, STATS)["result"] == "VOID"
    missing = settle_market("sot.total.over.7.5", FIXTURE, {})
    assert missing == {"result": "UNAVAILABLE", "reason": "missing_sot_statistics"}


def test_returns_apply_stake_tax_once_and_clv_uses_price_ratio() -> None:
    payout, pnl = selection_returns("WON", 1.70)
    assert payout == pytest.approx(1.496)
    assert pnl == pytest.approx(0.496)
    assert selection_returns("LOST", 1.70) == (0.0, -1.0)
    assert selection_returns("VOID", 1.70) == (1.0, 0.0)
    assert clv(1.80, 1.70) == pytest.approx(1.80 / 1.70 - 1)


def _selection(fixture_id: int, kickoff: str, market: str = "goals.total.over.2.5") -> dict:
    return {
        "rank": 1,
        "fixture_id": fixture_id,
        "fixture_date": kickoff,
        "home_team": "Home",
        "away_team": "Away",
        "market_key": market,
        "label": market,
        "group": market.split(".")[0],
        "league": {"code": "EPL"},
        "bookmaker": "Book",
        "bookmaker_id": 7,
        "odds": 1.70,
        "probability": 0.70,
        "conservative_probability": 0.68,
        "conservative_edge": 0.08,
        "conservative_net_ev": 0.10,
        "strategy_decision": "PAPER",
    }


def _save_single(store: PredictionStore, fixture_id: int, kickoff: str) -> int:
    store.save_scan(
        {
            "target_date": kickoff[:10],
            "strategy_version": DEFAULT_STRATEGY.name,
            "status": "completed",
            "singles": [_selection(fixture_id, kickoff)],
            "doubles": [],
        }
    )
    with store._connect() as conn:
        return int(conn.execute("SELECT id FROM scan_selections ORDER BY id DESC LIMIT 1").fetchone()[0])


def test_pending_settlement_filters_future_before_limit(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "pending.sqlite3")
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    past = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    _save_single(store, 1, future)
    past_id = _save_single(store, 2, past)
    rows = store.pending_settlement_entries(limit=1)
    assert [row["id"] for row in rows] == [past_id]


def test_reconciliation_is_idempotent_and_builds_validation_row(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "settle.sqlite3")
    kickoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    _save_single(store, 42, kickoff)
    assert store.save_closing_odds(42, {"market_key": "goals.total.over.2.5", "bookmaker": "Book", "bookmaker_id": 7, "odd": 1.60})
    with store._connect() as conn:
        conn.execute("UPDATE closing_odds_snapshots SET captured_at=?", ((datetime.fromisoformat(kickoff) - timedelta(minutes=5)).isoformat(),))

    class Provider:
        def fixture(self, fixture_id: int):
            return FIXTURE

        def fixture_statistics(self, fixture_id: int):
            return STATS

    engine = SettlementEngine(store, Provider())
    first = engine.reconcile()
    second = engine.reconcile()
    assert first["entries_settled"] == 1
    assert second["entries_settled"] == 0
    row = store.validation_rows()[0]
    assert row["pnl"] == pytest.approx(0.496)
    assert row["clv"] == pytest.approx(1.70 / 1.60 - 1)


def test_ticket_with_void_leg_uses_only_active_price(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "ticket.sqlite3")
    kickoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    legs = [_selection(1, kickoff), _selection(2, kickoff, "goals.total.over.3")]
    ticket = {
        "rank": 1,
        "ticket_type": "DOUBLE",
        "bookmaker": "Book",
        "odds": 2.89,
        "conservative_probability": 0.46,
        "conservative_edge": 0.08,
        "conservative_net_ev": 0.10,
        "strategy_decision": "PAPER",
        "legs": legs,
    }
    store.save_scan({"target_date": kickoff[:10], "strategy_version": "test", "status": "completed", "singles": [], "doubles": [ticket]})
    with store._connect() as conn:
        leg_rows = conn.execute("SELECT id FROM ticket_legs ORDER BY leg_number").fetchall()
    store.settle_ticket_leg(int(leg_rows[0][0]), {"result": "WON"}, 1.60, 1.70 / 1.60 - 1)
    store.settle_ticket_leg(int(leg_rows[1][0]), {"result": "VOID"}, None, None)
    assert store.aggregate_ticket_settlements() == 1
    with store._connect() as conn:
        row = conn.execute("SELECT result, closing_odds, pnl FROM ticket_settlements").fetchone()
    assert row["result"] == "WON"
    assert row["closing_odds"] == pytest.approx(1.60)
    assert row["pnl"] == pytest.approx(0.88 * 1.70 - 1)


def test_validation_gate_and_api_remain_paper_without_sample(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "api.sqlite3")
    report = validation_report(store)
    assert report["promotion_gate"]["decision"] == "PAPER"
    assert report["ticket_promotion_gate"]["eligible_for_bet"] is False

    class Legacy:
        def status(self):
            return {"status": "ok"}

        def teams(self):
            return []

    class Provider:
        def odds(self, fixture_id: int):
            return []

        def fixture(self, fixture_id: int):
            return {"status": "NS"}

    class Analysis:
        provider = Provider()

        def status(self):
            return {"status": "ok"}

        def leagues(self):
            return []

    client = TestClient(create_app(service=Legacy(), analysis_service=Analysis(), store=store))
    assert client.get("/api/validation/report").json()["promotion_gate"]["decision"] == "PAPER"
    assert client.post("/api/maintenance/run").status_code == 200
