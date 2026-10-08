"""Write the standardized grading/ export from the final full run (no model calls), then run the
course's zero-API self-check.

    uv run python scripts/export_grading.py --state state/full.sqlite --outputs runs/full-final

grading/ files: run.json, ingestion.json, records.jsonl.gz, membership.csv, ranking.csv, claims.csv,
calls.jsonl, checkpoint_before.json, checkpoint_after.json (the checkpoints are written during the
recorded interruption/resume and are only verified here).
"""

import argparse
import gzip
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.common import file_sha  # noqa: E402
from pipeline.export import record_json, write_calls  # noqa: E402

RAW = ROOT / "data" / "raw"
FULL_CSV = RAW / "spotify_reviews_18months.csv"
CHECKER = RAW / "check_submission.py"


def main(state, outputs):
    g = ROOT / "grading"
    g.mkdir(exist_ok=True)
    out = Path(outputs)
    con = sqlite3.connect(state)
    con.row_factory = sqlite3.Row

    (g / "run.json").write_text(json.dumps({
        "version": "a5-audit-v1", "analysis_count": 660622, "analysis_sha256": file_sha(FULL_CSV),
        "classification_input_fields": ["review_text"], "allow_multi_issue": False}))

    counts = {}
    with gzip.open(g / "records.jsonl.gz", "wt", encoding="utf-8") as f:
        for r in con.execute("SELECT * FROM records ORDER BY rowid"):
            rec = record_json(r)
            key = rec["status"] if rec["status"] == "completed" else f"quarantined:{rec['reason']}"
            counts[key] = counts.get(key, 0) + 1
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    (g / "records.jsonl").unlink(missing_ok=True)

    for name in ("membership.csv", "ranking.csv", "claims.csv"):
        shutil.copy(out / name, g / name)
    n_calls = write_calls(con, g / "calls.jsonl")  # every call made against the full-run state, all phases

    for name in ("checkpoint_before.json", "checkpoint_after.json"):
        if not (g / name).exists():
            print(f"WARNING: grading/{name} is missing")

    subprocess.run([sys.executable, "-I", str(CHECKER), "profile", "--full", str(FULL_CSV),
                    "--out", str(g / "ingestion.json")], check=True)
    ref = ROOT / "state" / "local-reference.json"
    subprocess.run([sys.executable, "-I", str(CHECKER), "reference", "--full", str(FULL_CSV), "--analysis",
                    str(FULL_CSV), "--out", str(ref)], check=True)
    report = ROOT / "evals" / "self-check.json"
    subprocess.run([sys.executable, "-I", str(CHECKER), "check", "--reference", str(ref), "--submission", str(g),
                    "--out", str(report)], check=True)
    r = json.loads(report.read_text())
    print(f"records: {counts} | calls exported: {n_calls}")
    print(f"self-check status: {r.get('status')} | coverage: {json.dumps(r.get('coverage'))}")
    print(f"working coverage point candidate: {r.get('working_coverage_point_candidate')} | issues: {r.get('issue_counts')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outputs", required=True)
    a = ap.parse_args()
    main(a.state, a.outputs)
