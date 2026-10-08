"""Shared helpers: exact source hashing (same as the course checker), CSV reading, state database."""

import csv
import hashlib
import json
import sqlite3
from pathlib import Path

FIELDS = ("review_id", "review_text", "review_rating", "review_likes", "app_version", "review_timestamp")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def row_sha(row):
    # Exact source strings: no trimming, translating or Unicode normalization.
    return hashlib.sha256(canonical([row[k] for k in FIELDS]).encode("utf-8")).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, strict=True)
        missing = [k for k in FIELDS if k not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Input CSV is missing columns: {missing}")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Malformed CSV row")
            yield row


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    review_id TEXT PRIMARY KEY,
    source_sha256 TEXT NOT NULL,
    text_sha256 TEXT,
    review_text TEXT,
    status TEXT NOT NULL,              -- pending | completed | quarantined
    reason TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    label_config TEXT,
    cache_source_id TEXT,
    topic TEXT, intent TEXT, sentiment REAL, severity INTEGER,
    entities TEXT, evidence_quote TEXT, needs_review INTEGER, quote_fallback INTEGER,
    run_id TEXT, updated_at TEXT,
    review_rating TEXT, review_likes TEXT, app_version TEXT, review_timestamp TEXT
);
CREATE INDEX IF NOT EXISTS records_text ON records(text_sha256);
CREATE INDEX IF NOT EXISTS records_status ON records(status);
-- Composite index: without it SQLite may pick records_status for "text_sha256=? AND status='pending'" and scan
-- every pending row per text (found at full scale: ~3 minutes per batch with 570k pending rows).
CREATE INDEX IF NOT EXISTS records_text_status ON records(text_sha256, status);

-- Result cache: one validated answer per (exact text, configuration).
CREATE TABLE IF NOT EXISTS results (
    text_sha256 TEXT NOT NULL,
    label_config TEXT NOT NULL,
    source_review_id TEXT NOT NULL,
    labels TEXT NOT NULL,
    PRIMARY KEY (text_sha256, label_config)
);

-- Verifier answers, cached by exact text + verifier configuration.
CREATE TABLE IF NOT EXISTS verify_results (
    text_sha256 TEXT NOT NULL,
    verify_config TEXT NOT NULL,
    review_id TEXT NOT NULL,
    labels TEXT NOT NULL,
    PRIMARY KEY (text_sha256, verify_config)
);

-- Downstream model outputs (issue names, memo), cached by a hash of their exact inputs.
CREATE TABLE IF NOT EXISTS artifacts (
    key TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    config TEXT NOT NULL,
    output TEXT NOT NULL,
    created_at TEXT
);

-- Every attempted model call, successful or not.
CREATE TABLE IF NOT EXISTS calls (
    call_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT, run_id TEXT, role TEXT, phase TEXT, model TEXT, effort TEXT,
    label_config TEXT, batch_no INTEGER, attempt INTEGER, review_ids TEXT,
    outcome TEXT, error TEXT, n_valid INTEGER,
    input_tokens INTEGER, cached_tokens INTEGER, output_tokens INTEGER, reasoning_tokens INTEGER,
    cost_usd REAL, started_at TEXT, duration_s REAL
);
"""


def connect(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    # Older state files: add source metadata columns if missing.
    cols = {r[1] for r in con.execute("PRAGMA table_info(records)")}
    for col in ("review_rating", "review_likes", "app_version", "review_timestamp"):
        if col not in cols:
            con.execute(f"ALTER TABLE records ADD COLUMN {col} TEXT")
    return con
