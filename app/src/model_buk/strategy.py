from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any, Iterable


@dataclass(frozen=True)
class StrategyProfile:
    """Frozen selection policy applied after the PURE probability model."""

    name: str = "pl_value_130_200_v2"
    mode: str = "PAPER"
    min_odds: float = 1.30
    max_odds: float = 2.00
    preferred_min_odds: float = 1.65
    preferred_max_odds: float = 1.80
    min_conservative_edge: float = 0.03
    min_conservative_net_ev: float = 0.05
    stake_tax_rate: float = 0.12
    winnings_cost_rate: float = 0.0
    max_odds_age_hours: float = 6.0
    fallback_probability_haircut: float = 0.03
    require_devig: bool = True
    require_validated_interval_for_bet: bool = True
    combo_predictive_validated: bool = False
    min_data_quality_score: float = 50.0
    max_single_per_fixture: int = 1
    combo_leg_min_odds: float = 1.15
    combo_leg_min_conservative_edge: float = 0.0
    combo_leg_min_conservative_raw_ev: float = 0.0
    max_combo_legs_per_fixture: int = 3
    max_combinations: int = 12

    def __post_init__(self) -> None:
        if self.mode not in {"PAPER", "BET"}:
            raise ValueError("Strategy mode must be PAPER or BET.")
        if not (1 < self.min_odds <= self.max_odds):
            raise ValueError("Invalid target odds interval.")
        if not (1 < self.combo_leg_min_odds <= self.max_odds):
            raise ValueError("Invalid minimum combination-leg odds.")
        if not (0 <= self.stake_tax_rate < 1 and 0 <= self.winnings_cost_rate < 1):
            raise ValueError("Cost rates must be fractions in [0, 1).")
        if not 0 <= self.fallback_probability_haircut < 1:
            raise ValueError("Probability haircut must be a fraction in [0, 1).")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def net_return(self, odds: float) -> float:
        return (1 - self.stake_tax_rate) * (
            1 + (float(odds) - 1) * (1 - self.winnings_cost_rate)
        )

    def break_even_probability(self, odds: float) -> float:
        return 1 / self.net_return(odds)


DEFAULT_STRATEGY = StrategyProfile()


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _fixture_id(analysis: dict[str, Any]) -> int | None:
    value = (analysis.get("fixture") or {}).get("fixture_id")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _base_candidates(
    analyses: Iterable[dict[str, Any]], profile: StrategyProfile
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for analysis in analyses:
        fixture = analysis.get("fixture") or {}
        fixture_id = _fixture_id(analysis)
        if fixture_id is None or analysis.get("prospective") is not True:
            continue
        quality = _finite((analysis.get("data_quality") or {}).get("score")) or 0.0
        if quality < profile.min_data_quality_score:
            continue
        for row in analysis.get("market_comparison") or []:
            odds = _finite(row.get("odds"))
            probability = _finite(row.get("probability"))
            conservative = _finite(row.get("conservative_probability"))
            market_probability = _finite(row.get("market_probability"))
            if None in (odds, probability, conservative, market_probability):
                continue
            if not row.get("odds_fresh") or row.get("interval_valid") is False:
                continue
            if profile.require_devig and row.get("devig_available") is not True:
                continue
            if row.get("settlement_compatible") is False:
                continue
            conservative_edge = conservative - market_probability
            conservative_net_ev = conservative * profile.net_return(odds) - 1
            validation_pass = bool(row.get("validation_pass"))
            decision = "BET" if profile.mode == "BET" and validation_pass else "PAPER"
            rows.append(
                {
                    **row,
                    "fixture_id": fixture_id,
                    "fixture_date": fixture.get("date"),
                    "home_team": fixture.get("home_team"),
                    "away_team": fixture.get("away_team"),
                    "league": analysis.get("league"),
                    "data_quality_score": quality,
                    "conservative_edge": conservative_edge,
                    "conservative_net_ev": conservative_net_ev,
                    "strategy_decision": decision,
                    "strategy_profile": profile.name,
                    "preferred_odds_band": profile.preferred_min_odds
                    <= odds
                    <= profile.preferred_max_odds,
                }
            )
    return rows


def _bookmaker_identity(row: dict[str, Any]) -> str:
    bookmaker_id = row.get("bookmaker_id")
    if bookmaker_id not in (None, ""):
        return f"id:{bookmaker_id}"
    return f"name:{str(row.get('bookmaker') or '').strip().casefold()}"


def _row_identity(row: dict[str, Any]) -> tuple[int, str, str]:
    return (
        int(row["fixture_id"]),
        str(row.get("market_key") or ""),
        _bookmaker_identity(row),
    )


def _rank_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        float(row["conservative_net_ev"]),
        float(row["conservative_edge"]),
        float(row["conservative_probability"]),
        float(row.get("odds") or 0),
    )


def select_singles(
    analyses: Iterable[dict[str, Any]], profile: StrategyProfile = DEFAULT_STRATEGY
) -> list[dict[str, Any]]:
    """Select at most N value candidates per fixture in the target odds band."""

    accepted = [
        row
        for row in _base_candidates(analyses, profile)
        if profile.min_odds <= float(row["odds"]) <= profile.max_odds
        and float(row["conservative_edge"]) >= profile.min_conservative_edge
        and float(row["conservative_net_ev"]) >= profile.min_conservative_net_ev
    ]
    by_fixture: dict[int, list[dict[str, Any]]] = {}
    for row in accepted:
        by_fixture.setdefault(int(row["fixture_id"]), []).append(row)
    selected = [
        row
        for fixture_rows in by_fixture.values()
        for row in sorted(fixture_rows, key=_rank_key, reverse=True)[
            : profile.max_single_per_fixture
        ]
    ]
    selected.sort(key=_rank_key, reverse=True)
    for rank, row in enumerate(selected, 1):
        row["rank"] = rank
        row["ticket_type"] = "SINGLE"
    return selected


def build_double_tickets(
    analyses: Iterable[dict[str, Any]], profile: StrategyProfile = DEFAULT_STRATEGY
) -> list[dict[str, Any]]:
    """Build two-leg tickets from different fixtures.

    Independence is enforced structurally at the information available here:
    legs must come from different matches. Same-match products are never made.
    The joint probability is therefore an explicit conditional assumption and
    remains PAPER until prospectively validated.
    """

    legs = [
        row
        for row in _base_candidates(analyses, profile)
        if float(row["odds"]) >= profile.combo_leg_min_odds
        and float(row["conservative_edge"]) >= profile.combo_leg_min_conservative_edge
        and float(row.get("conservative_raw_ev", -math.inf))
        >= profile.combo_leg_min_conservative_raw_ev
    ]
    by_fixture: dict[int, list[dict[str, Any]]] = {}
    for row in legs:
        by_fixture.setdefault(int(row["fixture_id"]), []).append(row)
    reduced = [
        row
        for fixture_rows in by_fixture.values()
        for row in sorted(fixture_rows, key=_rank_key, reverse=True)[
            : profile.max_combo_legs_per_fixture
        ]
    ]

    tickets: list[dict[str, Any]] = []
    for left, right in combinations(reduced, 2):
        if left["fixture_id"] == right["fixture_id"]:
            continue
        if not left.get("bookmaker") or _bookmaker_identity(left) != _bookmaker_identity(right):
            continue
        odds = float(left["odds"]) * float(right["odds"])
        if not profile.min_odds <= odds <= profile.max_odds:
            continue
        probability = float(left["probability"]) * float(right["probability"])
        conservative = float(left["conservative_probability"]) * float(
            right["conservative_probability"]
        )
        market_probability = float(left["market_probability"]) * float(
            right["market_probability"]
        )
        conservative_edge = conservative - market_probability
        conservative_net_ev = conservative * profile.net_return(odds) - 1
        if conservative_edge < profile.min_conservative_edge:
            continue
        if conservative_net_ev < profile.min_conservative_net_ev:
            continue
        validation_pass = bool(left.get("validation_pass")) and bool(
            right.get("validation_pass")
        )
        decision = (
            "BET"
            if profile.mode == "BET"
            and validation_pass
            and profile.combo_predictive_validated
            else "PAPER"
        )
        tickets.append(
            {
                "ticket_type": "DOUBLE",
                "strategy_profile": profile.name,
                "strategy_decision": decision,
                "odds": odds,
                "probability": probability,
                "conservative_probability": conservative,
                "market_probability": market_probability,
                "conservative_edge": conservative_edge,
                "conservative_net_ev": conservative_net_ev,
                "joint_probability_method": "independent_product_unvalidated",
                "bookmaker": left.get("bookmaker"),
                "preferred_odds_band": profile.preferred_min_odds
                <= odds
                <= profile.preferred_max_odds,
                "legs": [left, right],
            }
        )
    tickets.sort(
        key=lambda x: (
            float(x["conservative_net_ev"]),
            float(x["conservative_edge"]),
        ),
        reverse=True,
    )
    tickets = tickets[: profile.max_combinations]
    for rank, ticket in enumerate(tickets, 1):
        ticket["rank"] = rank
    return tickets


def build_strategy_scan(
    analyses: list[dict[str, Any]],
    profile: StrategyProfile = DEFAULT_STRATEGY,
    *,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    singles = select_singles(analyses, profile)
    doubles = build_double_tickets(analyses, profile)
    selected = {_row_identity(row) for row in singles}
    combo_legs = {
        _row_identity(leg)
        for ticket in doubles
        for leg in ticket.get("legs") or []
    }
    rejected: list[dict[str, Any]] = []
    for analysis in analyses:
        fixture = analysis.get("fixture") or {}
        fixture_id = _fixture_id(analysis)
        quality = _finite((analysis.get("data_quality") or {}).get("score")) or 0.0
        for row in analysis.get("market_comparison") or []:
            identity = (
                int(fixture_id) if fixture_id is not None else -1,
                str(row.get("market_key") or ""),
                _bookmaker_identity(row),
            )
            if fixture_id is None or identity in selected:
                continue
            odds = _finite(row.get("odds"))
            conservative = _finite(row.get("conservative_probability"))
            market_probability = _finite(row.get("market_probability"))
            codes: list[str] = []
            if analysis.get("prospective") is not True:
                codes.append("not_prospective")
            if quality < profile.min_data_quality_score:
                codes.append("data_quality")
            if odds is None or not profile.min_odds <= odds <= profile.max_odds:
                codes.append("target_odds")
            if not row.get("odds_fresh"):
                codes.append("stale_odds")
            if row.get("interval_valid") is False:
                codes.append("invalid_interval")
            if profile.require_validated_interval_for_bet and row.get("interval_available") is not True:
                codes.append("uncertainty")
            if row.get("validation_pass") is not True:
                codes.append("validation")
            if row.get("settlement_compatible") is False:
                codes.append("settlement")
            if profile.require_devig and row.get("devig_available") is not True:
                codes.append("devig")
            if conservative is None or market_probability is None:
                codes.append("missing_probability")
            else:
                if conservative - market_probability < profile.min_conservative_edge:
                    codes.append("edge")
                if odds is None or conservative * profile.net_return(odds) - 1 < profile.min_conservative_net_ev:
                    codes.append("net_ev")
            # A leg used in a valid combined ticket may be outside the target
            # single-odds band by design (for example 1.30 x 1.30 = 1.69).
            if identity in combo_legs and set(codes) == {"target_odds"}:
                continue
            if not codes:
                codes.append("fixture_rank_limit")
            if codes:
                rejected.append(
                    {
                        "fixture_id": fixture_id,
                        "home_team": fixture.get("home_team"),
                        "away_team": fixture.get("away_team"),
                        "market_key": row.get("market_key"),
                        "label": row.get("label"),
                        "bookmaker": row.get("bookmaker"),
                        "odds": odds,
                        "reason_codes": sorted(set(codes)),
                    }
                )
    rejected = rejected[:200]
    has_candidates = bool(singles or doubles)
    has_bet = any(
        item.get("strategy_decision") == "BET"
        for item in [*singles, *doubles]
    )
    return {
        "strategy_version": profile.name,
        "mode": profile.mode,
        "profile": profile.to_dict(),
        "fixture_count": len(analyses),
        "singles": singles,
        "doubles": doubles,
        "rejected": rejected,
        "errors": errors or [],
        "summary": {
            "single_count": len(singles),
            "double_count": len(doubles),
            "rejected_count": len(rejected),
            "decision": (
                "BET"
                if has_bet
                else "PAPER"
                if has_candidates
                else "NO BET"
            ),
        },
    }
