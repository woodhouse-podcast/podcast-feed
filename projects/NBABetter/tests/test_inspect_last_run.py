import importlib.util
import sqlite3
from pathlib import Path

import pytest


def load_module():
    """Load scripts/inspect_last_run.py as a module.

    We must register the module in sys.modules before exec_module because
    inspect_last_run uses `from __future__ import annotations` and dataclasses
    may resolve string annotations via sys.modules.
    """
    import sys

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "inspect_last_run.py"
    spec = importlib.util.spec_from_file_location("inspect_last_run", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parse_run_log_extracts_provider_mode_and_counters():
    mod = load_module()
    fixture = Path(__file__).parent / "fixtures" / "run-20260216T200140Z.log"
    summary = mod.parse_run_log(fixture)

    assert summary.filename == fixture.name
    assert summary.provider.lower() == "polymarket"
    assert summary.execution_mode == "PAPER"
    assert summary.schedule_updates == 2
    assert summary.schedule_no_games == 2
    assert summary.pending_resolve_checks == 1
    assert summary.pending_resolve_none == 1


def test_snapshot_db_counts_and_latest_timestamps(tmp_path):
    mod = load_module()
    db_path = tmp_path / "nba_betting.db"

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("CREATE TABLE odds_snapshots (id INTEGER PRIMARY KEY, timestamp TIMESTAMP)")
        cur.execute("CREATE TABLE notional_bets (id INTEGER PRIMARY KEY, timestamp TIMESTAMP)")
        cur.execute("CREATE TABLE games (id TEXT PRIMARY KEY, date TEXT)")
        cur.execute("CREATE TABLE markets (market_id TEXT PRIMARY KEY, last_updated TIMESTAMP)")
        cur.execute("CREATE TABLE model_estimates (id INTEGER PRIMARY KEY, timestamp TIMESTAMP)")
        cur.execute(
            "CREATE TABLE live_orders (id INTEGER PRIMARY KEY, updated_at TIMESTAMP, created_at TIMESTAMP)"
        )

        cur.execute("INSERT INTO odds_snapshots(timestamp) VALUES (?)", ("2026-02-16T20:01:43Z",))
        cur.execute("INSERT INTO odds_snapshots(timestamp) VALUES (?)", ("2026-02-17T09:00:00Z",))
        cur.execute("INSERT INTO notional_bets(timestamp) VALUES (?)", ("2026-02-17T08:00:00Z",))
        con.commit()
    finally:
        con.close()

    snap = mod.snapshot_db(str(db_path))
    by_table = {s.table: s for s in snap}

    assert by_table["odds_snapshots"].row_count == 2
    assert by_table["odds_snapshots"].latest_ts == "2026-02-17T09:00:00Z"

    assert by_table["notional_bets"].row_count == 1
    assert by_table["notional_bets"].latest_ts == "2026-02-17T08:00:00Z"


def test_format_report_includes_required_fields(tmp_path):
    mod = load_module()
    # Minimal db with required tables.
    db_path = tmp_path / "nba_betting.db"
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("CREATE TABLE odds_snapshots (id INTEGER PRIMARY KEY, timestamp TIMESTAMP)")
        cur.execute("CREATE TABLE notional_bets (id INTEGER PRIMARY KEY, timestamp TIMESTAMP)")
        cur.execute("CREATE TABLE games (id TEXT PRIMARY KEY, date TEXT)")
        cur.execute("CREATE TABLE markets (market_id TEXT PRIMARY KEY, last_updated TIMESTAMP)")
        cur.execute("CREATE TABLE model_estimates (id INTEGER PRIMARY KEY, timestamp TIMESTAMP)")
        cur.execute("CREATE TABLE live_orders (id INTEGER PRIMARY KEY, updated_at TIMESTAMP)")
        cur.execute("INSERT INTO odds_snapshots(timestamp) VALUES (?)", ("2026-02-17T09:00:00Z",))
        cur.execute("INSERT INTO notional_bets(timestamp) VALUES (?)", ("2026-02-17T08:00:00Z",))
        con.commit()
    finally:
        con.close()

    fixture = Path(__file__).parent / "fixtures" / "run-20260216T200140Z.log"
    log_summary = mod.parse_run_log(fixture)
    snapshots = mod.snapshot_db(str(db_path))

    report = mod.format_report(log_summary, snapshots, logs_dir=str(tmp_path), db_path=str(db_path))

    # Required fields per Acceptance Criteria.
    assert "[latest_log]" in report
    assert f"filename: {fixture.name}" in report
    assert "provider:" in report
    assert "execution_mode:" in report

    assert "[db_snapshot]" in report
    for table in [
        "games",
        "markets",
        "odds_snapshots",
        "notional_bets",
        "model_estimates",
        "live_orders",
    ]:
        assert f"{table}.row_count:" in report

    assert "odds_snapshots.latest_ts: 2026-02-17T09:00:00Z" in report
    assert "notional_bets.latest_ts: 2026-02-17T08:00:00Z" in report
