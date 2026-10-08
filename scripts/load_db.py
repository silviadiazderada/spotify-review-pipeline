"""Load processed results into the Postgres database that backs the dashboard (no model calls).

    uv run python scripts/load_db.py --state state/full.sqlite --outputs runs/full-final

Tables (replaced on every load, inside one transaction):
  reviews      one row per source review: labels, status, evidence quote, issue, source metadata, text
  issues       ranked issues with names, area and baseline metrics
  claims       claim IDs cited by the memo
  monthly      completed reviews and complaint records per month and decision area (for trends)
  outputs      saved analysis outputs (memo, memo check, evidence pack, verification, evaluations, run/cost summaries)
"""

import argparse
import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from pipeline.memo import AREAS  # noqa: E402

DDL = """
DROP TABLE IF EXISTS reviews, issues, claims, monthly, outputs;
CREATE TABLE reviews (
    review_id text PRIMARY KEY, status text NOT NULL, reason text,
    topic text, intent text, severity int, sentiment real, needs_review boolean,
    evidence_quote text, entities jsonb, cache_source_id text, label_config text,
    rating int, likes int, app_version text, review_ts timestamp, review_month text,
    area text, issue_id text, review_text text
);
CREATE TABLE issues (
    issue_id text PRIMARY KEY, topic text, subtopic text, area text, name text, description text,
    rank int, complaint_count int, severity_sum int, mean_severity numeric(10,6), priority_score int,
    example_review_ids text[]
);
CREATE TABLE claims (claim_id text PRIMARY KEY, issue_id text, metric text, value text);
CREATE TABLE monthly (month text, area text, completed int, complaints int, PRIMARY KEY (month, area));
CREATE TABLE outputs (key text PRIMARY KEY, content jsonb NOT NULL);
"""

INDEXES = """
CREATE INDEX reviews_issue ON reviews(issue_id);
CREATE INDEX reviews_status ON reviews(status);
CREATE INDEX reviews_month ON reviews(review_month);
"""


def read_csv(path):
    with Path(path).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def maybe_json(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None


def refresh_outputs(state, outputs):
    """Replace only the small analysis tables (issues, claims, outputs) inside one transaction. Use when the
    labelled reviews and issue membership are unchanged (e.g. a re-written memo)."""
    load_dotenv()
    out = Path(outputs)
    src = sqlite3.connect(state)
    src.row_factory = sqlite3.Row
    ranking = {r["issue_id"]: r for r in read_csv(out / "ranking.csv")}
    issues = read_csv(out / "issues.csv")
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=30) as pg, pg.transaction():
        same = pg.execute("SELECT COUNT(*) FROM reviews WHERE issue_id IS NOT NULL").fetchone()[0]
        if same != len(read_csv(out / "membership.csv")):
            raise SystemExit("membership changed - run a full load instead")
        overview = pg.execute("SELECT content FROM outputs WHERE key='overview_counts'").fetchone()
        pg.execute("DELETE FROM issues; DELETE FROM claims; DELETE FROM outputs")
        for i in issues:
            rk = ranking[i["issue_id"]]
            pg.execute("INSERT INTO issues VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                       (i["issue_id"], i["topic"], i["subtopic"], AREAS[i["topic"]], i["name"], i["description"],
                        int(rk["rank"]), int(rk["complaint_count"]), int(rk["severity_sum"]), rk["mean_severity"],
                        int(rk["priority_score"]), i["example_review_ids"].split()))
        for c in read_csv(out / "claims.csv"):
            pg.execute("INSERT INTO claims VALUES (%s,%s,%s,%s)", (c["claim_id"], c["issue_id"], c["metric"], c["value"]))
        for k, v in saved_outputs(out, src).items():
            if v is not None:
                pg.execute("INSERT INTO outputs VALUES (%s, %s)", (k, json.dumps(v)))
        if overview:
            pg.execute("INSERT INTO outputs VALUES ('overview_counts', %s)", (json.dumps(overview[0]),))
    print(f"Refreshed {len(issues)} issues, claims and outputs from {out}")


def saved_outputs(out, src):
    return {
        "memo_md": {"markdown": (out / "memo.md").read_text()} if (out / "memo.md").exists() else None,
        "memo_check": maybe_json(out / "memo_check.json"),
        "memo_audit": maybe_json(ROOT_DIR / "evals" / "memo_audit.json"),
        "evidence_pack": maybe_json(out / "evidence_pack.json"),
        "verify_report": maybe_json(out / "verify_report.json"),
        "run_summary": maybe_json(out / "run_summary.json"),
        "golden_eval": maybe_json("evals/golden_eval/summary.json"),
        "planted_gross": maybe_json("evals/planted_error/gross/planted_error_results.json"),
        "planted_subtle": maybe_json("evals/planted_error/subtle/planted_error_results.json"),
        "injection": maybe_json("evals/injection/injection_results.json"),
        "failure_paths": maybe_json("evals/failure_paths/failure_path_results.json"),
        "cost_checkpoints": maybe_json("cost/checkpoints.json"),
        "cost_pilot_runs": maybe_json("cost/pilot_runs.json"),
        "full_run_cost": {"by_run": [dict(r) for r in src.execute(
            "SELECT run_id, phase, role, COUNT(*) AS calls, SUM(outcome='failed') AS failed,"
            " ROUND(SUM(cost_usd), 4) AS cost_usd FROM calls GROUP BY run_id, phase, role ORDER BY MIN(call_id)")]},
    }


def main(state, outputs):
    load_dotenv()
    out = Path(outputs)
    src = sqlite3.connect(state)
    src.row_factory = sqlite3.Row
    membership = {m["review_id"]: m["issue_id"] for m in read_csv(out / "membership.csv")}
    ranking = {r["issue_id"]: r for r in read_csv(out / "ranking.csv")}
    issues = read_csv(out / "issues.csv")

    with psycopg.connect(os.environ["DATABASE_URL"]) as pg, pg.transaction():
        pg.execute(DDL)
        n = 0
        with pg.cursor().copy(
                "COPY reviews (review_id, status, reason, topic, intent, severity, sentiment, needs_review,"
                " evidence_quote, entities, cache_source_id, label_config, rating, likes, app_version, review_ts,"
                " review_month, area, issue_id, review_text) FROM STDIN") as cp:
            for r in src.execute("SELECT * FROM records ORDER BY rowid"):
                done = r["status"] == "completed"
                cp.write_row((
                    r["review_id"], r["status"], r["reason"] if r["status"] == "quarantined" else
                    ("pending_not_classified" if r["status"] == "pending" else None),
                    r["topic"], r["intent"], r["severity"], r["sentiment"],
                    bool(r["needs_review"]) if done else None, r["evidence_quote"], r["entities"],
                    r["cache_source_id"], r["label_config"],
                    int(r["review_rating"]) if (r["review_rating"] or "").isdigit() else None,
                    int(r["review_likes"]) if (r["review_likes"] or "").isdigit() else None,
                    r["app_version"] or None, r["review_timestamp"] or None, (r["review_timestamp"] or "")[:7] or None,
                    AREAS.get(r["topic"]) if done else None, membership.get(r["review_id"]), r["review_text"]))
                n += 1
        for i in issues:
            rk = ranking[i["issue_id"]]
            pg.execute("INSERT INTO issues VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                       (i["issue_id"], i["topic"], i["subtopic"], AREAS[i["topic"]], i["name"], i["description"],
                        int(rk["rank"]), int(rk["complaint_count"]), int(rk["severity_sum"]), rk["mean_severity"],
                        int(rk["priority_score"]), i["example_review_ids"].split()))
        for c in read_csv(out / "claims.csv"):
            pg.execute("INSERT INTO claims VALUES (%s,%s,%s,%s)", (c["claim_id"], c["issue_id"], c["metric"], c["value"]))
        pg.execute("""INSERT INTO monthly
            SELECT review_month, area, COUNT(*), COUNT(*) FILTER (WHERE intent IN ('complaint','cancellation'))
            FROM reviews WHERE status='completed' GROUP BY review_month, area""")
        saved = saved_outputs(out, src)
        for k, v in saved.items():
            if v is not None:
                pg.execute("INSERT INTO outputs VALUES (%s, %s)", (k, json.dumps(v)))
        # Precomputed overview counts (the dashboard reads these instead of scanning 660k rows per visit).
        overview = {
            "status": [dict(zip(("status", "reason", "n"), r)) for r in pg.execute(
                "SELECT status, reason, COUNT(*)::int FROM reviews GROUP BY status, reason ORDER BY 3 DESC").fetchall()],
            "intents": [dict(zip(("intent", "n"), r)) for r in pg.execute(
                "SELECT intent, COUNT(*)::int FROM reviews WHERE status='completed' GROUP BY intent ORDER BY 2 DESC").fetchall()],
            "areas": [dict(zip(("area", "complaints", "severity_sum"), r)) for r in pg.execute(
                "SELECT area, COUNT(*)::int, SUM(severity)::int FROM reviews WHERE status='completed'"
                " AND intent IN ('complaint','cancellation') GROUP BY area ORDER BY 3 DESC").fetchall()],
        }
        pg.execute("INSERT INTO outputs VALUES (%s, %s)", ("overview_counts", json.dumps(overview)))
        pg.execute(INDEXES)
        pg.execute("ANALYZE")
    with psycopg.connect(os.environ["DATABASE_URL"]) as pg:
        size = pg.execute("SELECT pg_size_pretty(pg_database_size(current_database()))").fetchone()[0]
        counts = pg.execute("SELECT status, COUNT(*) FROM reviews GROUP BY status ORDER BY 1").fetchall()
    print(f"Loaded {n:,} reviews {dict(counts)}, {len(issues)} issues; database size {size}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outputs", required=True)
    ap.add_argument("--outputs-only", action="store_true", help="refresh issues/claims/outputs; keep the reviews table")
    a = ap.parse_args()
    (refresh_outputs if a.outputs_only else main)(a.state, a.outputs)
