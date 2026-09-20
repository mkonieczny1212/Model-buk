from __future__ import annotations

import math
import re
import statistics
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from model_buk.odds_parser import normalize_odds


FINAL_STATUSES = {"FT", "AET", "PEN"}
COUNT_MARKET = re.compile(
    r"^(goals|corners|shots|sot|cards)\.(total|home|away)\.(over|under)\.([0-9]+(?:\.[0-9]+)?)$"
)


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def bookmaker_identity(row: dict[str, Any]) -> str:
    bookmaker_id = row.get("bookmaker_id")
    if bookmaker_id not in (None, ""):
        return f"id:{bookmaker_id}"
    return f"name:{str(row.get('bookmaker') or '').strip().casefold()}"


def settle_market(
    market_key: str,
    fixture: dict[str, Any],
    statistics_by_team: dict[int, dict[str, float | None]] | None = None,
) -> dict[str, Any]:
    """Resolve one supported 90-minute market from official result/statistics."""
    if str(fixture.get("status") or "").upper() not in FINAL_STATUSES:
        return {"result": "PENDING", "reason": "fixture_not_final"}
    home = fixture.get("home") or {}
    away = fixture.get("away") or {}
    home_goals = _finite(home.get("goals"))
    away_goals = _finite(away.get("goals"))
    if home_goals is None or away_goals is None:
        return {"result": "UNAVAILABLE", "reason": "missing_final_score"}

    if market_key == "result.home":
        won = home_goals > away_goals
        return {"result": "WON" if won else "LOST", "observed": home_goals - away_goals}
    if market_key == "result.draw":
        won = home_goals == away_goals
        return {"result": "WON" if won else "LOST", "observed": home_goals - away_goals}
    if market_key == "result.away":
        won = away_goals > home_goals
        return {"result": "WON" if won else "LOST", "observed": away_goals - home_goals}
    if market_key in {"btts.yes", "btts.no"}:
        yes = home_goals > 0 and away_goals > 0
        won = yes if market_key.endswith("yes") else not yes
        return {"result": "WON" if won else "LOST", "observed": bool(yes)}

    match = COUNT_MARKET.match(market_key)
    if not match:
        return {"result": "UNAVAILABLE", "reason": "unsupported_market"}
    metric, target, side, raw_line = match.groups()
    line = float(raw_line)
    if metric == "goals":
        home_value, away_value = home_goals, away_goals
    else:
        statistics_by_team = statistics_by_team or {}
        home_stats = statistics_by_team.get(int(home.get("id") or 0), {})
        away_stats = statistics_by_team.get(int(away.get("id") or 0), {})
        if metric == "cards":
            home_yellow, home_red = _finite(home_stats.get("yellow")), _finite(home_stats.get("red"))
            away_yellow, away_red = _finite(away_stats.get("yellow")), _finite(away_stats.get("red"))
            if None in (home_yellow, home_red, away_yellow, away_red):
                return {"result": "UNAVAILABLE", "reason": "missing_card_statistics"}
            home_value = home_yellow + 2 * home_red
            away_value = away_yellow + 2 * away_red
        else:
            home_value = _finite(home_stats.get(metric))
            away_value = _finite(away_stats.get(metric))
            if home_value is None or away_value is None:
                return {"result": "UNAVAILABLE", "reason": f"missing_{metric}_statistics"}
    observed = home_value + away_value if target == "total" else home_value if target == "home" else away_value
    if math.isclose(observed, line):
        return {"result": "VOID", "observed": observed, "line": line}
    won = observed > line if side == "over" else observed < line
    return {"result": "WON" if won else "LOST", "observed": observed, "line": line}


def selection_returns(result: str, odds: float, stake_tax_rate: float = 0.12) -> tuple[float, float]:
    if result == "WON":
        payout = (1 - stake_tax_rate) * float(odds)
        return payout, payout - 1
    if result == "LOST":
        return 0.0, -1.0
    if result == "VOID":
        return 1.0, 0.0
    raise ValueError(f"Cannot calculate return for {result}")


def clv(offered_odds: float, closing_odds: float | None) -> float | None:
    if closing_odds is None or closing_odds <= 1:
        return None
    return float(offered_odds) / float(closing_odds) - 1


@dataclass
class SettlementEngine:
    store: Any
    provider: Any
    stake_tax_rate: float = 0.12

    def capture_closing_odds(self, *, horizon_minutes: int = 180) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        due = self.store.pending_entries_for_closing(now, now + timedelta(minutes=horizon_minutes))
        fixture_ids = sorted({int(row["fixture_id"]) for row in due})
        saved = 0
        errors: list[dict[str, Any]] = []
        for fixture_id in fixture_ids:
            try:
                wanted = {
                    (str(row["market_key"]), bookmaker_identity(row.get("payload") or row))
                    for row in due
                    if int(row["fixture_id"]) == fixture_id
                }
                for row in normalize_odds(self.provider.odds(fixture_id)):
                    if (str(row["market_key"]), bookmaker_identity(row)) in wanted:
                        saved += int(self.store.save_closing_odds(fixture_id, row))
            except Exception as exc:
                errors.append({"fixture_id": fixture_id, "reason": type(exc).__name__})
        return {"fixtures_checked": len(fixture_ids), "snapshots_saved": saved, "errors": errors}

    def reconcile(self, *, limit: int = 100) -> dict[str, Any]:
        pending = self.store.pending_settlement_entries(limit=limit)
        by_fixture: dict[int, list[dict[str, Any]]] = {}
        for row in pending:
            by_fixture.setdefault(int(row["fixture_id"]), []).append(row)
        settled, unavailable = 0, 0
        errors: list[dict[str, Any]] = []
        for fixture_id, entries in by_fixture.items():
            try:
                fixture = self.provider.fixture(fixture_id)
                if str(fixture.get("status") or "").upper() not in FINAL_STATUSES:
                    continue
                needs_stats = any(not str(row["market_key"]).startswith(("result.", "btts.", "goals.")) for row in entries)
                stats = self.provider.fixture_statistics(fixture_id) if needs_stats else {}
                for row in entries:
                    outcome = settle_market(str(row["market_key"]), fixture, stats)
                    if outcome["result"] not in {"WON", "LOST", "VOID"}:
                        unavailable += 1
                        continue
                    closing = self.store.latest_closing_odds(
                        fixture_id,
                        str(row["market_key"]),
                        row.get("bookmaker"),
                        row.get("bookmaker_id"),
                        row.get("kickoff"),
                    )
                    closing_price = _finite((closing or {}).get("odds"))
                    row_clv = clv(float(row["odds"]), closing_price)
                    if row["entry_type"] == "single":
                        payout, pnl = selection_returns(outcome["result"], float(row["odds"]), self.stake_tax_rate)
                        self.store.settle_selection(row["id"], outcome, closing_price, row_clv, payout, pnl)
                    else:
                        self.store.settle_ticket_leg(row["id"], outcome, closing_price, row_clv)
                    settled += 1
            except Exception as exc:
                errors.append({"fixture_id": fixture_id, "reason": type(exc).__name__})
        tickets = self.store.aggregate_ticket_settlements(self.stake_tax_rate)
        return {
            "fixtures_checked": len(by_fixture),
            "entries_settled": settled,
            "entries_unavailable": unavailable,
            "tickets_settled": tickets,
            "errors": errors,
        }


def _calibration(rows: list[dict[str, Any]], bins: int = 10) -> dict[str, Any]:
    populated = []
    weighted_error = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        bucket = [r for r in rows if lower <= float(r["probability"]) < upper or index == bins - 1 and float(r["probability"]) == 1]
        if not bucket:
            continue
        predicted = statistics.fmean(float(r["probability"]) for r in bucket)
        observed = statistics.fmean(float(r["outcome"]) for r in bucket)
        error = abs(predicted - observed)
        weighted_error += len(bucket) * error
        populated.append({"lower": lower, "upper": upper, "count": len(bucket), "predicted": predicted, "observed": observed, "absolute_error": error})
    return {"ece": weighted_error / len(rows) if rows else None, "bins": populated}


def _segment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if not n:
        return {"count": 0}
    pnls = [float(r["pnl"]) for r in rows]
    clvs = [float(r["clv"]) for r in rows if r.get("clv") is not None]
    briers = [(float(r["probability"]) - float(r["outcome"])) ** 2 for r in rows]
    roi = statistics.fmean(pnls)
    roi_se = statistics.stdev(pnls) / math.sqrt(n) if n > 1 else None
    mean_clv = statistics.fmean(clvs) if clvs else None
    clv_se = statistics.stdev(clvs) / math.sqrt(len(clvs)) if len(clvs) > 1 else None
    calibration = _calibration(rows)
    return {
        "count": n,
        "wins": sum(int(r["outcome"]) for r in rows),
        "roi": roi,
        "roi_lower_95": roi - 1.96 * roi_se if roi_se is not None else None,
        "mean_clv": mean_clv,
        "clv_count": len(clvs),
        "clv_lower_95": mean_clv - 1.96 * clv_se if mean_clv is not None and clv_se is not None else None,
        "brier": statistics.fmean(briers),
        "ece": calibration["ece"],
        "calibration_bins": calibration["bins"],
    }


def validation_report(store: Any, *, min_sample: int = 200) -> dict[str, Any]:
    rows = store.validation_rows()
    ticket_rows = store.ticket_validation_rows()
    overall = _segment(rows)
    ticket_overall = _segment(ticket_rows)
    market_groups: dict[str, list[dict[str, Any]]] = {}
    league_groups: dict[str, list[dict[str, Any]]] = {}
    odds_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        market_groups.setdefault(str(row.get("market_group") or "other"), []).append(row)
        league_groups.setdefault(str(row.get("league_code") or "unknown"), []).append(row)
        odds = float(row["odds"])
        bucket = "1.50-1.64" if odds < 1.65 else "1.65-1.80" if odds <= 1.80 else "1.81-1.90"
        odds_groups.setdefault(bucket, []).append(row)
    gates = {
        "sample": overall.get("count", 0) >= min_sample,
        "roi_lower_95_positive": (overall.get("roi_lower_95") or -1) > 0,
        "clv_lower_95_positive": (overall.get("clv_lower_95") or -1) > 0,
        "ece_at_most_5pp": overall.get("ece") is not None and overall["ece"] <= 0.05,
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "tickets": ticket_overall,
        "by_market": {key: _segment(value) for key, value in sorted(market_groups.items())},
        "by_league": {key: _segment(value) for key, value in sorted(league_groups.items())},
        "by_odds": {key: _segment(value) for key, value in sorted(odds_groups.items())},
        "promotion_gate": {
            "minimum_sample": min_sample,
            "checks": gates,
            "eligible_for_bet": all(gates.values()),
            "decision": "BET_ELIGIBLE" if all(gates.values()) else "PAPER",
        },
        "ticket_promotion_gate": {
            "minimum_sample": min_sample,
            "statistical_checks_pass": ticket_overall.get("count", 0) >= min_sample
            and (ticket_overall.get("roi_lower_95") or -1) > 0
            and ticket_overall.get("ece") is not None
            and ticket_overall["ece"] <= 0.05,
            "eligible_for_bet": False,
            "decision": "PAPER",
            "reason": "Kupony wymagają osobnej próby i modelu zależności; sam ROI nie przełącza trybu.",
        },
    }


class MaintenanceWorker:
    def __init__(self, engine: SettlementEngine, interval_seconds: int = 900):
        self.engine = engine
        self.interval_seconds = max(60, int(interval_seconds))
        self.stop_event = threading.Event()
        self.run_lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.last_result: dict[str, Any] | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name="model-buk-maintenance", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def run_once(self) -> dict[str, Any]:
        with self.run_lock:
            result = {"captured": self.engine.capture_closing_odds(), "settled": self.engine.reconcile()}
            self.last_result = {"at": datetime.now(timezone.utc).isoformat(), **result}
            return self.last_result

    def _run(self) -> None:
        if self.stop_event.wait(30):
            return
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except Exception as exc:
                self.last_result = {"at": datetime.now(timezone.utc).isoformat(), "error": type(exc).__name__}
            self.stop_event.wait(self.interval_seconds)
