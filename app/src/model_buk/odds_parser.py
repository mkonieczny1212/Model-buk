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
    output = []
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
        output.append({**row, "market_key": key, "is_polish_hint": any(x in str(row.get("bookmaker", "")).lower() for x in POLISH_BOOKMAKER_HINTS)})
    return output


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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compare PURE probabilities to executable prices without using odds as features."""
    if not (0 <= stake_cost_rate < 1 and 0 <= winnings_cost_rate < 1):
        raise ValueError("Cost rates must be finite fractions in [0, 1).")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Odds evaluation time must include a timezone.")
    normalized = normalize_odds(raw_odds)
    model = {m["market_key"]: m for m in model_markets}
    by_book_market: dict[tuple[str, str], dict[str, Any]] = {}
    for row in normalized:
        by_book_market[(str(row.get("bookmaker")), row["market_key"])] = row

    result_devig: dict[tuple[str, str], float] = {}
    bookmakers = {str(row.get("bookmaker")) for row in normalized}
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
        devig = result_devig.get((str(row.get("bookmaker")), key))
        partner = _two_way_partner(key)
        if partner:
            other = by_book_market.get((str(row.get("bookmaker")), partner))
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
        reasons = []
        if not eligible or m.get("predictive_validated") is not True:
            reasons.append("Brak potwierdzonej walidacji predykcyjnej lub jakości danych.")
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
        interval = m.get("probability_interval")
        conservative = probability
        if interval is not None:
            try:
                lower = float(interval.get("lower") if isinstance(interval, dict) else interval[0])
                upper = float(interval.get("upper") if isinstance(interval, dict) else interval[1])
                if not (0 <= lower <= probability <= upper <= 1):
                    raise ValueError("Invalid interval")
                conservative = lower
            except (TypeError, ValueError, IndexError, KeyError):
                reasons.append("Nieprawidłowy przedział niepewności prognozy.")
        if key.startswith("cards.") and (not m.get("settlement_rule") or row.get("settlement_rule") != m.get("settlement_rule")):
            reasons.append("Niepotwierdzona zgodność zasad rozliczenia kartek.")
        net_return = (1 - stake_cost_rate) * (1 + (price - 1) * (1 - winnings_cost_rate))
        net_ev = probability * net_return - 1
        conservative_ev = conservative * net_return - 1
        if conservative - market_p < min_edge or conservative_ev < min_ev:
            reasons.append("Konserwatywne edge i EV po kosztach nie spełniają progów.")
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
            "conservative_probability": conservative,
            "cost_assumptions": {"stake_cost_rate": stake_cost_rate, "winnings_cost_rate": winnings_cost_rate, "configured": bool(stake_cost_rate or winnings_cost_rate)},
            "odds_fresh": fresh,
            "odds_age_hours": age,
            "decision": decision,
            "decision_reason": reason,
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
    for key, rows in grouped.items():
        polish = [r for r in rows if r.get("polish_bookmaker_hint")]
        candidates = polish if prefer_polish and polish else rows
        best_rows.append(max(candidates, key=lambda r: (r["decision"] == "BET", r["odds_fresh"], r["odds"], r["ev"])))

    best_rows.sort(key=lambda r: (r["decision"] == "BET", r.get("ev", -999), r.get("probability", 0), r.get("edge", -999)), reverse=True)
    opportunities = [r for r in best_rows if r["decision"] == "BET"]
    return opportunities, best_rows
