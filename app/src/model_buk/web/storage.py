from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_runs_created_at ON scan_runs(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_selections_run ON scan_selections(scan_run_id, rank)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_tickets_run ON scan_tickets(scan_run_id, rank)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ticket_legs_ticket ON ticket_legs(ticket_id, leg_number)")

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
