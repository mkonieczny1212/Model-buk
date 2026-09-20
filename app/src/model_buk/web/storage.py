from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StoredPrediction:
    id: int
    created_at: str
    fixture_date: str
    home_team: str
    away_team: str
    model_version: str
    decision: str | None
    payload: dict[str, Any]


class PredictionStore:
    """Append-only local research registry.

    Predictions and odds snapshots are kept separately. This preserves the PURE
    model output and makes later CLV/line-movement analysis possible.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    fixture_date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    decision TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at DESC)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS odds_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    fixture_id INTEGER,
                    bookmaker TEXT,
                    market_key TEXT,
                    odds REAL NOT NULL,
                    provider_update TEXT,
                    raw_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_odds_fixture_market ON odds_snapshots(fixture_id, market_key, created_at)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER NOT NULL REFERENCES scan_runs(id),
                    rank INTEGER NOT NULL,
                    fixture_id INTEGER NOT NULL,
                    market_key TEXT NOT NULL,
                    bookmaker TEXT NOT NULL,
                    odds REAL NOT NULL,
                    conservative_probability REAL NOT NULL,
                    conservative_edge REAL NOT NULL,
                    conservative_net_ev REAL NOT NULL,
                    decision TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(scan_run_id, fixture_id, market_key, bookmaker)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER NOT NULL REFERENCES scan_runs(id),
                    rank INTEGER NOT NULL,
                    ticket_type TEXT NOT NULL,
                    bookmaker TEXT NOT NULL,
                    combined_odds REAL NOT NULL,
                    conservative_probability REAL NOT NULL,
                    conservative_edge REAL NOT NULL,
                    conservative_net_ev REAL NOT NULL,
                    decision TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS selection_settlements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    selection_id INTEGER NOT NULL UNIQUE REFERENCES scan_selections(id),
                    settled_at TEXT NOT NULL,
                    result TEXT NOT NULL,
                    closing_odds REAL,
                    clv REAL,
                    payout REAL,
                    pnl REAL,
                    raw_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_legs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL REFERENCES scan_tickets(id),
                    leg_number INTEGER NOT NULL,
                    fixture_id INTEGER NOT NULL,
                    market_key TEXT NOT NULL,
                    bookmaker TEXT NOT NULL,
                    odds REAL NOT NULL,
                    conservative_probability REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(ticket_id, leg_number)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_leg_settlements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_leg_id INTEGER NOT NULL UNIQUE REFERENCES ticket_legs(id),
                    settled_at TEXT NOT NULL,
                    result TEXT NOT NULL,
                    closing_odds REAL,
                    clv REAL,
                    raw_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS closing_odds_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL,
                    fixture_id INTEGER NOT NULL,
                    bookmaker TEXT NOT NULL,
                    bookmaker_id TEXT,
                    market_key TEXT NOT NULL,
                    odds REAL NOT NULL,
                    provider_update TEXT,
                    raw_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_settlements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL UNIQUE REFERENCES scan_tickets(id),
                    settled_at TEXT NOT NULL,
                    result TEXT NOT NULL,
                    closing_odds REAL,
                    clv REAL,
                    payout REAL NOT NULL,
                    pnl REAL NOT NULL,
                    raw_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_runs_created_at ON scan_runs(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_selections_run ON scan_selections(scan_run_id, rank)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_tickets_run ON scan_tickets(scan_run_id, rank)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ticket_legs_ticket ON ticket_legs(ticket_id, leg_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_closing_fixture_market ON closing_odds_snapshots(fixture_id, market_key, captured_at DESC)")
            # Forward compatible upgrades for databases created by development
            # builds before the complete v0.9 settlement schema was frozen.
            ticket_columns = {row[1] for row in conn.execute("PRAGMA table_info(ticket_settlements)")}
            for name, declaration in (
                ("closing_odds", "REAL"),
                ("clv", "REAL"),
                ("payout", "REAL NOT NULL DEFAULT 0"),
                ("pnl", "REAL NOT NULL DEFAULT 0"),
                ("raw_json", "TEXT NOT NULL DEFAULT '{}'")
            ):
                if name not in ticket_columns:
                    conn.execute(f"ALTER TABLE ticket_settlements ADD COLUMN {name} {declaration}")

    def save(self, payload: dict[str, Any]) -> int:
        fixture = payload.get("fixture", {})
        opportunities = payload.get("opportunities") or []
        strategy_singles = (payload.get("strategy") or {}).get("singles") or []
        best = opportunities[0] if opportunities else strategy_singles[0] if strategy_singles else {}
        model_version = payload.get("engine_version") or payload.get("suite_version") or payload.get("model_version") or "unknown"
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO predictions (
                    created_at, fixture_date, home_team, away_team,
                    model_version, decision, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    str(fixture.get("date") or fixture.get("kickoff") or ""),
                    str(fixture.get("home_team") or (fixture.get("home") or {}).get("name") or ""),
                    str(fixture.get("away_team") or (fixture.get("away") or {}).get("name") or ""),
                    str(model_version),
                    best.get("strategy_decision") or best.get("decision"),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid)

    def save_odds(self, fixture_id: int | None, odds_rows: list[dict[str, Any]]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        with self._connect() as conn:
            for row in odds_rows:
                market_key = row.get("market_key")
                if not market_key:
                    continue
                conn.execute(
                    """
                    INSERT INTO odds_snapshots (
                        created_at, fixture_id, bookmaker, market_key, odds,
                        provider_update, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now,
                        fixture_id,
                        str(row.get("bookmaker") or ""),
                        str(market_key),
                        float(row["odd"]),
                        row.get("update"),
                        json.dumps(row, ensure_ascii=False),
                    ),
                )
                count += 1
        return count

    def recent_odds(self, fixture_id: int, market_key: str, bookmaker: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        sql = "SELECT * FROM odds_snapshots WHERE fixture_id=? AND market_key=?"
        params: list[Any] = [fixture_id, market_key]
        if bookmaker:
            sql += " AND bookmaker=?"
            params.append(bookmaker)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 200)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def recent(self, limit: int = 20) -> list[StoredPrediction]:
        limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [
            StoredPrediction(
                id=int(row["id"]),
                created_at=str(row["created_at"]),
                fixture_date=str(row["fixture_date"]),
                home_team=str(row["home_team"]),
                away_team=str(row["away_team"]),
                model_version=str(row["model_version"]),
                decision=row["decision"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        ]

    def save_scan(self, payload: dict[str, Any]) -> int:
        """Freeze a complete strategy run and its priced selections."""
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO scan_runs (
                    created_at, target_date, strategy_version, status, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    str(payload.get("target_date") or ""),
                    str(payload.get("strategy_version") or "unknown"),
                    str(payload.get("status") or "completed"),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            run_id = int(cur.lastrowid)
            for item in payload.get("singles") or []:
                conn.execute(
                    """
                    INSERT INTO scan_selections (
                        scan_run_id, rank, fixture_id, market_key, bookmaker,
                        odds, conservative_probability, conservative_edge,
                        conservative_net_ev, decision, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        int(item.get("rank") or 0),
                        int(item["fixture_id"]),
                        str(item["market_key"]),
                        str(item.get("bookmaker") or ""),
                        float(item["odds"]),
                        float(item["conservative_probability"]),
                        float(item["conservative_edge"]),
                        float(item["conservative_net_ev"]),
                        str(item.get("strategy_decision") or "PAPER"),
                        json.dumps(item, ensure_ascii=False),
                    ),
                )
            for item in payload.get("doubles") or []:
                ticket_cur = conn.execute(
                    """
                    INSERT INTO scan_tickets (
                        scan_run_id, rank, ticket_type, bookmaker, combined_odds,
                        conservative_probability, conservative_edge,
                        conservative_net_ev, decision, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        int(item.get("rank") or 0),
                        str(item.get("ticket_type") or "DOUBLE"),
                        str(item.get("bookmaker") or ""),
                        float(item["odds"]),
                        float(item["conservative_probability"]),
                        float(item["conservative_edge"]),
                        float(item["conservative_net_ev"]),
                        str(item.get("strategy_decision") or "PAPER"),
                        json.dumps(item, ensure_ascii=False),
                    ),
                )
                ticket_id = int(ticket_cur.lastrowid)
                for leg_number, leg in enumerate(item.get("legs") or [], 1):
                    conn.execute(
                        """
                        INSERT INTO ticket_legs (
                            ticket_id, leg_number, fixture_id, market_key,
                            bookmaker, odds, conservative_probability, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ticket_id,
                            leg_number,
                            int(leg["fixture_id"]),
                            str(leg["market_key"]),
                            str(leg.get("bookmaker") or ""),
                            float(leg["odds"]),
                            float(leg["conservative_probability"]),
                            json.dumps(leg, ensure_ascii=False),
                        ),
                    )
        return run_id

    def recent_scans(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, created_at, target_date, strategy_version, status, payload_json FROM scan_runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "created_at": str(row["created_at"]),
                "target_date": str(row["target_date"]),
                "strategy_version": str(row["strategy_version"]),
                "status": str(row["status"]),
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    @staticmethod
    def _kickoff(payload: dict[str, Any]) -> datetime | None:
        value = payload.get("fixture_date") or payload.get("kickoff")
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None

    def pending_entries_for_closing(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with self._connect() as conn:
            singles = conn.execute(
                """
                SELECT s.id, s.fixture_id, s.market_key, s.bookmaker, s.odds, s.payload_json
                FROM scan_selections s
                LEFT JOIN selection_settlements x ON x.selection_id=s.id
                WHERE x.id IS NULL
                """
            ).fetchall()
            legs = conn.execute(
                """
                SELECT l.id, l.fixture_id, l.market_key, l.bookmaker, l.odds, l.payload_json
                FROM ticket_legs l
                LEFT JOIN ticket_leg_settlements x ON x.ticket_leg_id=l.id
                WHERE x.id IS NULL
                """
            ).fetchall()
        for row in [*singles, *legs]:
            payload = json.loads(row["payload_json"])
            kickoff = self._kickoff(payload)
            if kickoff is not None and start <= kickoff <= end:
                rows.append({**dict(row), **{"payload": payload, "kickoff": kickoff.isoformat()}})
        return rows

    def pending_settlement_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        output: list[dict[str, Any]] = []
        with self._connect() as conn:
            singles = conn.execute(
                """
                SELECT s.id, s.fixture_id, s.market_key, s.bookmaker, s.odds, s.payload_json
                FROM scan_selections s
                LEFT JOIN selection_settlements x ON x.selection_id=s.id
                WHERE x.id IS NULL ORDER BY s.id
                """
            ).fetchall()
            legs = conn.execute(
                """
                SELECT l.id, l.fixture_id, l.market_key, l.bookmaker, l.odds, l.payload_json
                FROM ticket_legs l
                LEFT JOIN ticket_leg_settlements x ON x.ticket_leg_id=l.id
                WHERE x.id IS NULL ORDER BY l.id
                """
            ).fetchall()
        settlement_cutoff = datetime.now(timezone.utc) - timedelta(minutes=100)
        for entry_type, rows in (("single", singles), ("ticket_leg", legs)):
            for row in rows:
                payload = json.loads(row["payload_json"])
                kickoff = self._kickoff(payload)
                if kickoff is None or kickoff > settlement_cutoff:
                    continue
                output.append(
                    {
                        **dict(row),
                        "entry_type": entry_type,
                        "bookmaker_id": payload.get("bookmaker_id"),
                        "kickoff": kickoff.isoformat(),
                    }
                )
        return output[:limit]

    def save_closing_odds(self, fixture_id: int, row: dict[str, Any]) -> bool:
        market_key = row.get("market_key")
        try:
            odds = float(row["odd"])
        except (KeyError, TypeError, ValueError):
            return False
        if not market_key or odds <= 1:
            return False
        captured_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            identity_sql = " AND bookmaker_id=?" if row.get("bookmaker_id") is not None else " AND bookmaker=?"
            identity_value = str(row.get("bookmaker_id")) if row.get("bookmaker_id") is not None else str(row.get("bookmaker") or "")
            latest = conn.execute(
                f"""
                SELECT odds, provider_update FROM closing_odds_snapshots
                WHERE fixture_id=? AND market_key=? {identity_sql}
                ORDER BY id DESC LIMIT 1
                """,
                (fixture_id, str(market_key), identity_value),
            ).fetchone()
            if latest and float(latest["odds"]) == odds and latest["provider_update"] == row.get("update"):
                return False
            conn.execute(
                """
                INSERT INTO closing_odds_snapshots (
                    captured_at, fixture_id, bookmaker, bookmaker_id,
                    market_key, odds, provider_update, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    captured_at,
                    int(fixture_id),
                    str(row.get("bookmaker") or ""),
                    str(row.get("bookmaker_id")) if row.get("bookmaker_id") is not None else None,
                    str(market_key),
                    odds,
                    row.get("update"),
                    json.dumps(row, ensure_ascii=False),
                ),
            )
        return True

    def latest_closing_odds(
        self,
        fixture_id: int,
        market_key: str,
        bookmaker: str | None,
        bookmaker_id: Any = None,
        kickoff: str | None = None,
    ) -> dict[str, Any] | None:
        sql = "SELECT * FROM closing_odds_snapshots WHERE fixture_id=? AND market_key=?"
        params: list[Any] = [int(fixture_id), str(market_key)]
        if bookmaker_id not in (None, ""):
            sql += " AND bookmaker_id=?"
            params.append(str(bookmaker_id))
        elif bookmaker:
            sql += " AND bookmaker=?"
            params.append(str(bookmaker))
        if kickoff:
            sql += " AND captured_at<=?"
            params.append(str(kickoff))
        sql += " ORDER BY captured_at DESC, id DESC LIMIT 1"
        with self._connect() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None

    def settle_selection(
        self,
        selection_id: int,
        outcome: dict[str, Any],
        closing_odds: float | None,
        clv: float | None,
        payout: float,
        pnl: float,
    ) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO selection_settlements (
                    selection_id, settled_at, result, closing_odds, clv,
                    payout, pnl, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (selection_id, datetime.now(timezone.utc).isoformat(), outcome["result"], closing_odds, clv, payout, pnl, json.dumps(outcome, ensure_ascii=False)),
            )
        return cur.rowcount == 1

    def settle_ticket_leg(
        self,
        leg_id: int,
        outcome: dict[str, Any],
        closing_odds: float | None,
        clv: float | None,
    ) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO ticket_leg_settlements (
                    ticket_leg_id, settled_at, result, closing_odds, clv, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (leg_id, datetime.now(timezone.utc).isoformat(), outcome["result"], closing_odds, clv, json.dumps(outcome, ensure_ascii=False)),
            )
        return cur.rowcount == 1

    def aggregate_ticket_settlements(self, stake_tax_rate: float = 0.12) -> int:
        settled = 0
        with self._connect() as conn:
            tickets = conn.execute(
                """
                SELECT t.id, t.combined_odds
                FROM scan_tickets t
                LEFT JOIN ticket_settlements x ON x.ticket_id=t.id
                WHERE x.id IS NULL
                """
            ).fetchall()
            for ticket in tickets:
                legs = conn.execute(
                    """
                    SELECT l.id, l.odds, x.result, x.closing_odds FROM ticket_legs l
                    LEFT JOIN ticket_leg_settlements x ON x.ticket_leg_id=l.id
                    WHERE l.ticket_id=? ORDER BY l.leg_number
                    """,
                    (ticket["id"],),
                ).fetchall()
                if not legs or any(row["result"] is None for row in legs):
                    continue
                results = [str(row["result"]) for row in legs]
                result = "LOST" if "LOST" in results else "VOID" if all(x == "VOID" for x in results) else "WON"
                effective_odds = float(ticket["combined_odds"])
                if result == "WON" and "VOID" in results:
                    active_ids = [int(row["id"]) for row in legs if row["result"] == "WON"]
                    placeholders = ",".join("?" for _ in active_ids)
                    active = conn.execute(f"SELECT odds FROM ticket_legs WHERE id IN ({placeholders})", active_ids).fetchall()
                    effective_odds = math.prod(float(row["odds"]) for row in active)
                closing_prices = [float(row["closing_odds"]) for row in legs if row["result"] != "VOID" and row["closing_odds"] is not None]
                active_leg_count = sum(row["result"] != "VOID" for row in legs)
                closing_odds = math.prod(closing_prices) if len(closing_prices) == active_leg_count and active_leg_count else None
                ticket_clv = effective_odds / closing_odds - 1 if closing_odds and closing_odds > 1 else None
                if result == "WON":
                    payout = (1 - stake_tax_rate) * effective_odds
                    pnl = payout - 1
                elif result == "LOST":
                    payout, pnl = 0.0, -1.0
                else:
                    payout, pnl = 1.0, 0.0
                conn.execute(
                    """
                    INSERT INTO ticket_settlements (
                        ticket_id, settled_at, result, closing_odds, clv,
                        payout, pnl, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ticket["id"], datetime.now(timezone.utc).isoformat(), result, closing_odds, ticket_clv, payout, pnl, json.dumps({"leg_results": results, "effective_odds": effective_odds})),
                )
                settled += 1
        return settled

    def validation_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.odds, s.payload_json, x.result, x.clv, x.pnl
                FROM scan_selections s
                JOIN selection_settlements x ON x.selection_id=s.id
                WHERE x.result IN ('WON','LOST')
                ORDER BY s.id
                """
            ).fetchall()
        output = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            league = payload.get("league") or {}
            output.append(
                {
                    "odds": float(row["odds"]),
                    "probability": float(payload.get("probability") or payload.get("conservative_probability")),
                    "outcome": 1 if row["result"] == "WON" else 0,
                    "pnl": float(row["pnl"]),
                    "clv": row["clv"],
                    "market_group": payload.get("group") or str(payload.get("market_key") or "").split(".")[0],
                    "league_code": league.get("code") or payload.get("league_code"),
                }
            )
        return output

    def ticket_validation_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT t.combined_odds, t.conservative_probability, x.result, x.pnl, x.clv
                FROM scan_tickets t JOIN ticket_settlements x ON x.ticket_id=t.id
                WHERE x.result IN ('WON','LOST') ORDER BY t.id
                """
            ).fetchall()
        return [
            {
                "odds": float(row["combined_odds"]),
                "probability": float(row["conservative_probability"]),
                "outcome": 1 if row["result"] == "WON" else 0,
                "pnl": float(row["pnl"]),
                "clv": row["clv"],
                "market_group": "double",
                "league_code": "multi",
            }
            for row in rows
        ]
