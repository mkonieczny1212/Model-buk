from __future__ import annotations

import re
import math
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any

from model_buk.markets.pricing import devig_two_way, expected_value


BET_ID_MAP = {
    1: ("result", "result"),
    5: ("goals", "total"),
    8: ("btts", "btts"),
    16: ("goals", "home"),
    17: ("goals", "away"),
    45: ("corners", "total"),
    57: ("corners", "home"),
    58: ("corners", "away"),
    80: ("cards", "total"),
    82: ("cards", "home"),
    83: ("cards", "away"),
    87: ("sot", "total"),
    88: ("sot", "home"),
    89: ("sot", "away"),
    211: ("shots", "total"),
    220: ("shots", "away"),
    221: ("shots", "home"),
    243: ("sot", "home"),
    244: ("sot", "away"),
}

POLISH_BOOKMAKER_HINTS = ("sts", "betclic", "superbet", "fortuna", "betfan")


def _bookmaker_key(row: dict[str, Any]) -> str:
    bookmaker_id = row.get("bookmaker_id")
    if bookmaker_id not in (None, ""):
        return f"id:{bookmaker_id}"
    return f"name:{str(row.get('bookmaker') or '').strip().casefold()}"


def _parse_ou(value: str) -> tuple[str, float] | None:
    m = re.match(r"^(Over|Under)\s+([0-9]+(?:\.[0-9]+)?)$", str(value).strip(), flags=re.I)
    if not m:
        return None
    return m.group(1).lower(), float(m.group(2))


def to_market_key(row: dict[str, Any]) -> str | None:
    try:
        bet_id = int(row.get("bet_id") or 0)
    except (TypeError, ValueError):
        return None
    if bet_id == 1:
        value = str(row.get("value") or "").strip().lower()
        return {"home": "result.home", "draw": "result.draw", "away": "result.away"}.get(value)
    if bet_id == 8:
        value = str(row.get("value") or "").strip().lower()
        return {"yes": "btts.yes", "no": "btts.no"}.get(value)
    mapped = BET_ID_MAP.get(bet_id)
    if not mapped:
        return None
    metric, target = mapped
    parsed = _parse_ou(str(row.get("value") or ""))
    if not parsed:
        return None
    side, line = parsed
    # Model Buk v0.5 prices .5 thresholds only. Asian integer/quarter lines are
    # deliberately not coerced into a different payoff structure.
    if abs((line * 2) - round(line * 2)) > 1e-9 or abs(line - (int(line) + 0.5)) > 1e-9:
        return None
    return f"{metric}.{target}.{side}.{line}"


def normalize_odds(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    def order_key(row: dict[str, Any]) -> tuple[float, float]:
        try:
            updated = datetime.fromisoformat(str(row.get("update")).replace("Z", "+00:00"))
            stamp = updated.timestamp() if updated.tzinfo is not None else float("-inf")
        except (TypeError, ValueError):
            stamp = float("-inf")
        return stamp, float(row["odd"])

    for row in raw:
        try:
            price = float(row.get("odd"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(price) or price <= 1:
            continue
        key = to_market_key(row)
        if not key:
            continue
        normalized = {**row, "market_key": key, "is_polish_hint": any(x in str(row.get("bookmaker", "")).lower() for x in POLISH_BOOKMAKER_HINTS)}
        identity = (_bookmaker_key(row), key)
        current = output.get(identity)
        if current is None or order_key(normalized) > order_key(current):
            output[identity] = normalized
    return list(output.values())


def _two_way_partner(key: str) -> str | None:
    if ".over." in key:
        return key.replace(".over.", ".under.")
    if ".under." in key:
        return key.replace(".under.", ".over.")
    if key == "btts.yes":
        return "btts.no"
    if key == "btts.no":
        return "btts.yes"
    return None


def rank_opportunities(
    model_markets: list[dict[str, Any]],
    raw_odds: list[dict[str, Any]],
    min_edge: float = 0.05,
    min_ev: float = 0.05,
    prefer_polish: bool = True,
    *,
    now: datetime | None = None,
    max_odds_age_hours: float = 6.0,
    stake_cost_rate: float = 0.0,
    winnings_cost_rate: float = 0.0,
    min_odds: float | None = None,
    max_odds: float | None = None,
    fallback_probability_haircut: float = 0.0,
    require_interval_for_bet: bool = False,
    keep_all_bookmakers: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compare PURE probabilities to executable prices without using odds as features."""
    if not (0 <= stake_cost_rate < 1 and 0 <= winnings_cost_rate < 1):
        raise ValueError("Cost rates must be finite fractions in [0, 1).")
    if not 0 <= fallback_probability_haircut < 1:
        raise ValueError("Probability haircut must be a fraction in [0, 1).")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Odds evaluation time must include a timezone.")
    normalized = normalize_odds(raw_odds)
    model = {m["market_key"]: m for m in model_markets}
    by_book_market: dict[tuple[str, str], dict[str, Any]] = {}
    for row in normalized:
        by_book_market[(_bookmaker_key(row), row["market_key"])] = row

    result_devig: dict[tuple[str, str], float] = {}
    bookmakers = {_bookmaker_key(row) for row in normalized}
    for bookmaker in bookmakers:
        trio = [by_book_market.get((bookmaker, key)) for key in ("result.home", "result.draw", "result.away")]
        if all(trio):
            implied = [1.0 / float(x["odd"]) for x in trio]
            denom = sum(implied)
            if denom > 0:
                for key, q in zip(("result.home", "result.draw", "result.away"), implied):
                    result_devig[(bookmaker, key)] = q / denom

    compared: list[dict[str, Any]] = []
    for row in normalized:
        key = row["market_key"]
        m = model.get(key)
        if not m:
            continue
        price = float(row["odd"])
        p_market = 1.0 / price
        bookmaker = _bookmaker_key(row)
        devig = result_devig.get((bookmaker, key))
        partner = _two_way_partner(key)
        if partner:
            other = by_book_market.get((bookmaker, partner))
            if other:
                if ".under." in key or key == "btts.no":
                    over_p, under_p = devig_two_way(float(other["odd"]), price)
                    devig = under_p
                else:
                    over_p, under_p = devig_two_way(price, float(other["odd"]))
                    devig = over_p
        market_p = float(devig if devig is not None else p_market)
        try:
            probability = float(m["probability"])
        except (TypeError, ValueError, KeyError):
            continue
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            continue
        edge = probability - market_p
        ev = expected_value(probability, price)
        eligible = bool(m.get("eligible_for_bet", False))
        validation_pass = eligible and m.get("predictive_validated") is True
        reasons = []
        reason_codes = []
        if not validation_pass:
            reasons.append("Brak potwierdzonej walidacji predykcyjnej lub jakości danych.")
            reason_codes.append("validation")
        try:
            updated = datetime.fromisoformat(str(row.get("update")).replace("Z", "+00:00"))
            if updated.tzinfo is None:
                raise ValueError("Timezone missing")
            age = (now - updated).total_seconds() / 3600
            fresh = 0 <= age <= max_odds_age_hours
        except (TypeError, ValueError):
            age, fresh = None, False
        if not fresh:
            reasons.append("Kurs nie ma potwierdzonej aktualności.")
            reason_codes.append("stale_odds")
        interval = m.get("probability_interval")
        conservative = max(0.0, probability - fallback_probability_haircut)
        conservative_basis = (
            "configured_probability_haircut"
            if fallback_probability_haircut
            else "point_estimate"
        )
        interval_available = interval is not None
        interval_valid = True
        if interval is not None:
            try:
                lower = float(interval.get("lower") if isinstance(interval, dict) else interval[0])
                upper = float(interval.get("upper") if isinstance(interval, dict) else interval[1])
                if not (0 <= lower <= probability <= upper <= 1):
                    raise ValueError("Invalid interval")
                conservative = lower
                conservative_basis = "model_interval_lower_bound"
            except (TypeError, ValueError, IndexError, KeyError):
                reasons.append("Nieprawidłowy przedział niepewności prognozy.")
                reason_codes.append("invalid_interval")
                interval_valid = False
        if require_interval_for_bet and (not interval_available or not interval_valid):
            validation_pass = False
            if "uncertainty" not in reason_codes:
                reasons.append("Brak poprawnego, zwalidowanego przedziału niepewności prognozy.")
                reason_codes.append("uncertainty")
        settlement_compatible = not key.startswith("cards.") or bool(
            m.get("settlement_rule")
            and row.get("settlement_rule") == m.get("settlement_rule")
        )
        if not settlement_compatible:
            reasons.append("Niepotwierdzona zgodność zasad rozliczenia kartek.")
            reason_codes.append("settlement")
        net_return = (1 - stake_cost_rate) * (1 + (price - 1) * (1 - winnings_cost_rate))
        net_ev = probability * net_return - 1
        conservative_ev = conservative * net_return - 1
        conservative_raw_ev = conservative * price - 1
        conservative_edge = conservative - market_p
        target_odds_pass = (min_odds is None or price >= min_odds) and (
            max_odds is None or price <= max_odds
        )
        if not target_odds_pass:
            reasons.append("Kurs końcowy jest poza zakresem aktywnego profilu.")
            reason_codes.append("target_odds")
        value_pass = conservative - market_p >= min_edge and conservative_ev >= min_ev
        if not value_pass:
            reasons.append("Konserwatywne edge i EV po kosztach nie spełniają progów.")
            reason_codes.append("value")
        decision = "NO BET" if reasons else "BET"
        reason = " ".join(reasons) if reasons else "Walidacja, aktualność kursu oraz konserwatywne edge i EV po kosztach spełniają progi."
        compared.append({
            **m,
            "bookmaker": row.get("bookmaker"),
            "bookmaker_id": row.get("bookmaker_id"),
            "odds": price,
            "market_probability": market_p,
            "raw_implied_probability": p_market,
            "devig_available": devig is not None,
            "edge": edge,
            "ev": ev,
            "net_ev": net_ev,
            "conservative_ev": conservative_ev,
            "conservative_raw_ev": conservative_raw_ev,
            "conservative_edge": conservative_edge,
            "conservative_probability": conservative,
            "conservative_probability_basis": conservative_basis,
            "cost_assumptions": {"stake_cost_rate": stake_cost_rate, "winnings_cost_rate": winnings_cost_rate, "configured": bool(stake_cost_rate or winnings_cost_rate)},
            "odds_fresh": fresh,
            "odds_age_hours": age,
            "decision": decision,
            "decision_reason": reason,
            "reason_codes": reason_codes,
            "validation_pass": validation_pass,
            "interval_valid": interval_valid,
            "interval_available": interval_available,
            "settlement_compatible": settlement_compatible,
            "value_pass": value_pass,
            "target_odds_pass": target_odds_pass,
            "eligible_for_bet": eligible,
            "odds_update": row.get("update"),
            "polish_bookmaker_hint": row.get("is_polish_hint", False),
        })

    # One best executable price per model market; prefer Polish bookmaker only when
    # it is actually present, otherwise keep the best observed price and label it.
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in compared:
        grouped[row["market_key"]].append(row)
    best_rows: list[dict[str, Any]] = []
    if keep_all_bookmakers:
        best_rows = list(compared)
    else:
        for key, rows in grouped.items():
            polish = [r for r in rows if r.get("polish_bookmaker_hint")]
            candidates = polish if prefer_polish and polish else rows
            best_rows.append(max(candidates, key=lambda r: (r["decision"] == "BET", r["odds_fresh"], r["odds"], r["ev"])))

    best_rows.sort(key=lambda r: (r["decision"] == "BET", r.get("conservative_ev", -999), r.get("conservative_edge", -999), r.get("probability", 0)), reverse=True)
    opportunities = [r for r in best_rows if r["decision"] == "BET"]
    return opportunities, best_rows
