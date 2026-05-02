"""SQLite database setup. Single-file DB at ./perf_sentinel.db."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("perf_sentinel.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id               TEXT PRIMARY KEY,
    target           TEXT NOT NULL,
    commit_sha       TEXT,
    branch           TEXT,
    started_at       TEXT NOT NULL,
    duration_seconds REAL,
    status           TEXT NOT NULL,
    ci_url           TEXT,
    raw_artifact     TEXT
);

CREATE TABLE IF NOT EXISTS benchmarks (
    id        INTEGER PRIMARY KEY,
    run_id    TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    metric    TEXT NOT NULL,
    value     REAL NOT NULL,
    unit      TEXT NOT NULL,
    baseline  REAL,
    delta_pct REAL
);

CREATE INDEX IF NOT EXISTS idx_benchmarks_run    ON benchmarks(run_id);
CREATE INDEX IF NOT EXISTS idx_benchmarks_name   ON benchmarks(name);
CREATE INDEX IF NOT EXISTS idx_runs_target_time  ON runs(target, started_at DESC);
"""


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()