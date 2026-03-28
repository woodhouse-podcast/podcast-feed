#!/usr/bin/env python3
"""Inspect the most recent NBABetter run deterministically.

This script is intentionally offline-only (no network access).
It summarizes:
- newest run-*.log file under --logs
- key fields parsed from that log (provider + execution mode + a few counters)
- sqlite DB snapshot (row counts + latest timestamps) under --db

Usage:
  python3 scripts/inspect_last_run.py --db ./nba_betting.db --logs ./logs
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Be strict to avoid accidentally matching unrelated files.
RE_RUN_LOG = re.compile(r"^run-.*\.log$")


@dataclass(frozen=True)
class LogSummary:
    filename: str
    provider: Optional[str]
    execution_mode: Optional[str]
    schedule_updates: int
    schedule_no_games: int
    pending_resolve_checks: int
    pending_resolve_none: int


@dataclass(frozen=True)
class TableSnapshot:
    table: str
    row_count: Optional[int]
    latest_ts: Optional[str]


def _safe_int(val: Any) -> Optional[int]:
    try:
        if val is None:
            return None
        return int(val)
    except Exception:
        return None


def find_latest_run_log(logs_dir: str) -> Optional[Path]:
    p = Path(logs_dir)
    if not p.exists() or not p.is_dir():
        return None

    candidates: List[Path] = []
    for child in p.iterdir():
        if child.is_file() and RE_RUN_LOG.search(child.name):
            candidates.append(child)

    if not candidates:
        return None

    # Newest by modification time; tie-breaker by filename to be deterministic.
    candidates.sort(key=lambda x: (x.stat().st_mtime, x.name))
    return candidates[-1]


def parse_run_log(log_path: Path) -> LogSummary:
    provider: Optional[str] = None
    execution_mode: Optional[str] = None
    schedule_updates = 0
    schedule_no_games = 0
    pending_resolve_checks = 0
    pending_resolve_none = 0

    # Patterns designed to match existing logs but degrade gracefully.
    re_provider_primary = re.compile(r"Using (.+?) as primary provider", re.IGNORECASE)
    re_provider_forced = re.compile(r"Execution routing FORCED to:\s*(\w+)", re.IGNORECASE)
    re_exec_mode = re.compile(r"Execution mode is (\w+)", re.IGNORECASE)

    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if provider is None:
                m = re_provider_primary.search(line)
                if m:
                    provider = m.group(1).strip()
            if provider is None:
                m = re_provider_forced.search(line)
                if m:
                    provider = m.group(1).strip()

            if execution_mode is None:
                m = re_exec_mode.search(line)
                if m:
                    execution_mode = m.group(1).strip().upper()

            if "DAILY SCHEDULE UPDATE" in line:
                schedule_updates += 1
            if "No NBA games found for today" in line:
                schedule_no_games += 1

            if "Checking for pending bets to resolve" in line:
                pending_resolve_checks += 1
            if "No pending bets found" in line:
                pending_resolve_none += 1

    return LogSummary(
        filename=log_path.name,
        provider=provider,
        execution_mode=execution_mode,
        schedule_updates=schedule_updates,
        schedule_no_games=schedule_no_games,
        pending_resolve_checks=pending_resolve_checks,
        pending_resolve_none=pending_resolve_none,
    )


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def _pick_latest_ts_expr(table: str) -> Optional[str]:
    # Known timestamp columns per table.
    if table == "games":
        return "MAX(date)"
    if table == "markets":
        return "MAX(last_updated)"
    if table in {"odds_snapshots", "notional_bets", "model_estimates"}:
        return "MAX(timestamp)"
    if table == "live_orders":
        # Prefer updated_at when present; fall back to created_at.
        return None
    return None


def snapshot_db(db_path: str) -> List[TableSnapshot]:
    tables = [
        "games",
        "markets",
        "odds_snapshots",
        "notional_bets",
        "model_estimates",
        "live_orders",
    ]

    if not db_path:
        raise ValueError("--db is required")

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB not found: {db_path}")

    # Prefer read-only connection to avoid any risk of modifying the DB during inspection.
    # (Falls back to a normal connection if the SQLite build/URI mode isn't available.)
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except Exception:
        con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        out: List[TableSnapshot] = []
        for t in tables:
            if not _table_exists(cur, t):
                out.append(TableSnapshot(table=t, row_count=None, latest_ts=None))
                continue

            cur.execute(f"SELECT COUNT(*) FROM {t}")
            row_count = _safe_int(cur.fetchone()[0])

            latest_ts: Optional[str] = None
            if t == "live_orders":
                # Try updated_at then created_at if those columns exist.
                cur.execute(f"PRAGMA table_info({t})")
                cols = {r[1] for r in cur.fetchall()}
                if "updated_at" in cols:
                    cur.execute(f"SELECT MAX(updated_at) FROM {t}")
                    latest_ts = cur.fetchone()[0]
                elif "created_at" in cols:
                    cur.execute(f"SELECT MAX(created_at) FROM {t}")
                    latest_ts = cur.fetchone()[0]
            else:
                expr = _pick_latest_ts_expr(t)
                if expr:
                    cur.execute(f"SELECT {expr} FROM {t}")
                    latest_ts = cur.fetchone()[0]

            if latest_ts is not None:
                latest_ts = str(latest_ts)

            out.append(TableSnapshot(table=t, row_count=row_count, latest_ts=latest_ts))

        return out
    finally:
        con.close()


def format_report(
    log: Optional[LogSummary],
    snapshots: List[TableSnapshot],
    logs_dir: str,
    db_path: str,
) -> str:
    lines: List[str] = []
    lines.append("NBABetter - Last Run Inspection Report")
    # Deterministic UTC timestamp (timezone-aware).
    now = datetime.now(timezone.utc)
    lines.append(f"generated_utc: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"logs_dir: {logs_dir}")
    lines.append(f"db_path: {db_path}")
    lines.append("")

    lines.append("[latest_log]")
    if log is None:
        lines.append("filename: (none found)")
        lines.append("provider: (unknown)")
        lines.append("execution_mode: (unknown)")
    else:
        lines.append(f"filename: {log.filename}")
        lines.append(f"provider: {log.provider or '(unknown)'}")
        lines.append(f"execution_mode: {log.execution_mode or '(unknown)'}")
        lines.append(f"schedule_updates: {log.schedule_updates}")
        lines.append(f"schedule_no_games: {log.schedule_no_games}")
        lines.append(f"pending_resolve_checks: {log.pending_resolve_checks}")
        lines.append(f"pending_resolve_none: {log.pending_resolve_none}")

    lines.append("")
    lines.append("[db_snapshot]")
    for s in snapshots:
        count = "(missing)" if s.row_count is None else str(s.row_count)
        lines.append(f"{s.table}.row_count: {count}")
        # Always include latest_ts field (Acceptance Criteria wants odds_snapshots + notional_bets)
        ts = s.latest_ts if s.latest_ts is not None else "(none)"
        lines.append(f"{s.table}.latest_ts: {ts}")

    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the most recent bot run (logs + DB snapshot)")
    parser.add_argument("--db", required=True, help="Path to sqlite DB (e.g., ./nba_betting.db)")
    parser.add_argument("--logs", required=True, help="Directory containing run-*.log files")
    args = parser.parse_args(argv)

    latest = find_latest_run_log(args.logs)
    log_summary = parse_run_log(latest) if latest else None

    snapshots = snapshot_db(args.db)
    report = format_report(log_summary, snapshots, logs_dir=args.logs, db_path=args.db)
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
