from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from model_buk.strategy import (
    DEFAULT_STRATEGY,
    StrategyProfile,
    build_double_tickets,
    build_strategy_scan,
    select_singles,
)
from model_buk.odds_parser import rank_opportunities
from model_buk.web.api import create_app
from model_buk.web.service import MatchAnalysisService
from model_buk.web.storage import PredictionStore


def analysis(
    fixture_id: int,
    *,
    odds: float,
    probability: float,
    conservative: float,
    market_probability: float,
    bookmaker: str = "Book",
    market_key: str = "goals.total.over.2.5",
) -> dict:
    raw_ev = conservative * odds - 1
    return {
        "prospective": True,
        "fixture": {
            "fixture_id": fixture_id,
            "date": "2026-10-01T18:00:00+00:00",
            "home_team": f"Home {fixture_id}",
            "away_team": f"Away {fixture_id}",
        },
        "league": {"code": "EPL", "name": "Premier League"},
        "data_quality": {"score": 80},
        "market_comparison": [
            {
                "market_key": market_key,
                "label": "Powyżej 2.5",
                "group": "goals",
                "bookmaker": bookmaker,
                "odds": odds,
                "probability": probability,
                "conservative_probability": conservative,
                "market_probability": market_probability,
                "devig_available": True,
                "conservative_raw_ev": raw_ev,
                "odds_fresh": True,
                "interval_valid": True,
                "settlement_compatible": True,
                "validation_pass": False,
            }
        ],
    }


@pytest.mark.parametrize("odds", [1.50, 1.90])
def test_single_target_odds_boundaries_are_inclusive(odds: float) -> None:
    p = 0.90
    rows = select_singles(
        [analysis(1, odds=odds, probability=p, conservative=p, market_probability=0.70)]
    )
    assert len(rows) == 1
    assert rows[0]["strategy_decision"] == "PAPER"


def test_only_best_single_from_fixture_is_kept() -> None:
    first = analysis(1, odds=1.70, probability=.80, conservative=.80, market_probability=.60)
    second = analysis(1, odds=1.80, probability=.80, conservative=.80, market_probability=.60,
                      market_key="goals.total.under.3.5")
    first["market_comparison"].extend(second["market_comparison"])
    rows = select_singles([first])
    assert len(rows) == 1
    assert rows[0]["market_key"] == "goals.total.under.3.5"


def test_130_times_130_is_priced_once_after_tax() -> None:
    rows = build_double_tickets(
        [
            analysis(1, odds=1.30, probability=.86, conservative=.85, market_probability=.75),
            analysis(2, odds=1.30, probability=.86, conservative=.85, market_probability=.75),
        ]
    )
    assert len(rows) == 1
    ticket = rows[0]
    assert ticket["odds"] == pytest.approx(1.69)
    assert ticket["conservative_probability"] == pytest.approx(.85 * .85)
    assert ticket["conservative_net_ev"] == pytest.approx(.85 * .85 * .88 * 1.69 - 1)
    assert ticket["strategy_decision"] == "PAPER"


def test_attractive_combined_odds_without_value_are_rejected() -> None:
    rows = build_double_tickets(
        [
            analysis(1, odds=1.30, probability=.80, conservative=.80, market_probability=.76),
            analysis(2, odds=1.30, probability=.80, conservative=.80, market_probability=.76),
        ]
    )
    assert rows == []


def test_double_requires_different_fixtures_and_same_bookmaker() -> None:
    same_fixture = analysis(1, odds=1.30, probability=.90, conservative=.89, market_probability=.70)
    same_fixture["market_comparison"].append(
        analysis(1, odds=1.30, probability=.90, conservative=.89, market_probability=.70,
                 market_key="btts.yes")["market_comparison"][0]
    )
    assert build_double_tickets([same_fixture]) == []
    assert build_double_tickets(
        [
            analysis(1, odds=1.30, probability=.90, conservative=.89, market_probability=.70, bookmaker="A"),
            analysis(2, odds=1.30, probability=.90, conservative=.89, market_probability=.70, bookmaker="B"),
        ]
    ) == []


def test_same_bookmaker_name_with_different_ids_is_not_combined() -> None:
    left = analysis(1, odds=1.30, probability=.90, conservative=.89, market_probability=.70)
    right = analysis(2, odds=1.30, probability=.90, conservative=.89, market_probability=.70)
    left["market_comparison"][0]["bookmaker_id"] = 10
    right["market_comparison"][0]["bookmaker_id"] = 11
    assert build_double_tickets([left, right]) == []


def test_bet_profile_does_not_promote_unvalidated_candidates() -> None:
    profile = StrategyProfile(mode="BET")
    scan = build_strategy_scan(
        [analysis(1, odds=1.70, probability=.90, conservative=.89, market_probability=.60)],
        profile,
    )
    assert scan["singles"][0]["strategy_decision"] == "PAPER"
    assert scan["summary"]["decision"] == "PAPER"


def test_combination_requires_its_own_predictive_validation() -> None:
    profile = StrategyProfile(mode="BET", combo_predictive_validated=False)
    inputs = [
        analysis(1, odds=1.30, probability=.90, conservative=.89, market_probability=.70),
        analysis(2, odds=1.30, probability=.90, conservative=.89, market_probability=.70),
    ]
    for item in inputs:
        item["market_comparison"][0]["validation_pass"] = True
    ticket = build_double_tickets(inputs, profile)[0]
    assert ticket["strategy_decision"] == "PAPER"
    assert ticket["joint_probability_method"] == "independent_product_unvalidated"


def test_strategy_requires_complete_market_devig() -> None:
    item = analysis(1, odds=1.70, probability=.90, conservative=.89, market_probability=.60)
    item["market_comparison"][0]["devig_available"] = False
    assert select_singles([item]) == []


def test_missing_interval_gets_configured_probability_haircut() -> None:
    now = "2026-09-20T12:00:00+00:00"
    model = [
        {
            "market_key": "goals.total.over.2.5",
            "probability": .80,
            "eligible_for_bet": True,
            "predictive_validated": True,
        },
        {
            "market_key": "goals.total.under.2.5",
            "probability": .20,
            "eligible_for_bet": True,
            "predictive_validated": True,
        },
    ]
    raw = [
        {"bookmaker": "Book", "bet_id": 5, "value": "Over 2.5", "odd": 1.70, "update": now},
        {"bookmaker": "Book", "bet_id": 5, "value": "Under 2.5", "odd": 2.20, "update": now},
    ]
    _, rows = rank_opportunities(
        model,
        raw,
        now=__import__("datetime").datetime.fromisoformat(now),
        fallback_probability_haircut=.03,
    )
    over = next(row for row in rows if row["market_key"] == "goals.total.over.2.5")
    assert over["conservative_probability"] == pytest.approx(.77)
    assert over["conservative_probability_basis"] == "configured_probability_haircut"


def test_missing_interval_blocks_bet_when_required() -> None:
    now = "2026-09-20T12:00:00+00:00"
    model = [
        {"market_key": "btts.yes", "probability": .80, "eligible_for_bet": True, "predictive_validated": True},
        {"market_key": "btts.no", "probability": .20, "eligible_for_bet": True, "predictive_validated": True},
    ]
    raw = [
        {"bookmaker": "Book", "bet_id": 8, "value": "Yes", "odd": 1.70, "update": now},
        {"bookmaker": "Book", "bet_id": 8, "value": "No", "odd": 2.20, "update": now},
    ]
    opportunities, rows = rank_opportunities(
        model,
        raw,
        now=__import__("datetime").datetime.fromisoformat(now),
        require_interval_for_bet=True,
    )
    assert opportunities == []
    assert rows[0]["interval_available"] is False
    assert "uncertainty" in rows[0]["reason_codes"]


def test_all_bookmakers_are_retained_for_cross_fixture_matching() -> None:
    now = "2026-09-20T12:00:00+00:00"
    model = [
        {"market_key": "btts.yes", "probability": .80, "eligible_for_bet": True, "predictive_validated": True},
        {"market_key": "btts.no", "probability": .20, "eligible_for_bet": True, "predictive_validated": True},
    ]
    raw = []
    for bookmaker, yes_price in (("A", 1.80), ("C", 1.70)):
        raw.extend([
            {"bookmaker": bookmaker, "bet_id": 8, "value": "Yes", "odd": yes_price, "update": now},
            {"bookmaker": bookmaker, "bet_id": 8, "value": "No", "odd": 2.20, "update": now},
        ])
    _, rows = rank_opportunities(
        model,
        raw,
        now=__import__("datetime").datetime.fromisoformat(now),
        keep_all_bookmakers=True,
    )
    assert {row["bookmaker"] for row in rows if row["market_key"] == "btts.yes"} == {"A", "C"}


def test_scan_storage_is_additive_and_round_trips(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "model.sqlite3")
    payload = {
        "target_date": "2026-10-01",
        "strategy_version": DEFAULT_STRATEGY.name,
        "status": "completed",
        "singles": select_singles(
            [analysis(1, odds=1.70, probability=.85, conservative=.84, market_probability=.65)]
        ),
        "doubles": [],
    }
    run_id = store.save_scan(payload)
    saved = store.recent_scans(1)
    assert saved[0]["id"] == run_id
    assert saved[0]["payload"]["strategy_version"] == DEFAULT_STRATEGY.name


def test_scan_storage_persists_combination_legs(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "legs.sqlite3")
    doubles = build_double_tickets([
        analysis(1, odds=1.30, probability=.90, conservative=.89, market_probability=.70),
        analysis(2, odds=1.30, probability=.90, conservative=.89, market_probability=.70),
    ])
    store.save_scan({
        "target_date": "2026-10-01",
        "strategy_version": DEFAULT_STRATEGY.name,
        "status": "completed",
        "singles": [],
        "doubles": doubles,
    })
    with store._connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ticket_legs").fetchone()[0] == 2


def test_scan_api_can_persist_one_frozen_run(tmp_path: Path) -> None:
    class Legacy:
        def status(self):
            return {"status": "ok"}

        def teams(self):
            return []

    class Analysis:
        def status(self):
            return {"status": "ok"}

        def scan_fixtures(self, date, league_codes, max_fixtures, deep):
            return {
                "target_date": date,
                "strategy_version": DEFAULT_STRATEGY.name,
                "status": "completed",
                "singles": [],
                "doubles": [],
                "errors": [],
                "summary": {"single_count": 0, "double_count": 0},
            }

    store = PredictionStore(tmp_path / "api.sqlite3")
    client = TestClient(create_app(service=Legacy(), analysis_service=Analysis(), store=store))
    response = client.post(
        "/api/scan",
        json={"date": "2026-10-01", "league_codes": ["EPL"], "max_fixtures": 5},
    )
    assert response.status_code == 200
    assert response.json()["scan_id"] == 1
    assert len(client.get("/api/scans").json()["scans"]) == 1


def test_scanner_skips_started_matches_before_applying_limit() -> None:
    service = object.__new__(MatchAnalysisService)
    service.strategy = DEFAULT_STRATEGY
    service.fixtures = lambda date, league_codes: {
        "mode": "live",
        "fixtures": [
            {"fixture_id": 1, "kickoff": "2020-01-01T10:00:00+00:00", "status": "FT"},
            {"fixture_id": 2, "kickoff": "2099-01-01T10:00:00+00:00", "status": "NS"},
        ],
    }
    service.analyze_fixture = lambda fixture_id, deep=False: analysis(
        fixture_id,
        odds=1.70,
        probability=.85,
        conservative=.84,
        market_probability=.65,
    )
    result = service.scan_fixtures("2099-01-01", ["EPL"], max_fixtures=1)
    assert result["requested_fixture_count"] == 1
    assert result["fixture_count"] == 1
    assert result["singles"][0]["fixture_id"] == 2
    assert result["skipped_non_prospective_count"] == 1
