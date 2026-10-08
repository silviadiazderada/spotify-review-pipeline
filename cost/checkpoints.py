"""Refresh full-run estimates from the 500- and 10,000-review development checkpoints (no model calls).

    uv run python cost/checkpoints.py      # writes cost/checkpoints.json (read by cost/calculator.py)
"""

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHECKPOINTS = [
    ("checkpoint_500", "state/dev500.sqlite", ["dev-500"], 1),
    ("analysis_10000", "state/dev10k.sqlite", ["dev-10k-w2", "dev-10k-w8", "dev-10k-requeue"], 8),
]


def main():
    out = {}
    for name, db, runs, workers in CHECKPOINTS:
        con = sqlite3.connect(ROOT / db)
        q = f"run_id IN ({','.join('?' * len(runs))})"
        e = con.execute(f"SELECT COUNT(*), SUM(outcome='failed'), SUM(input_tokens), SUM(cached_tokens), SUM(output_tokens),"
                        f" SUM(cost_usd), SUM(duration_s) FROM calls WHERE role='enrich' AND {q}", runs).fetchone()
        sent = sum(len(json.loads(r[0])) for r in con.execute(
            f"SELECT review_ids FROM calls WHERE role='enrich' AND outcome='succeeded' AND {q}", runs))
        v = con.execute(f"SELECT COUNT(*), SUM(cost_usd), SUM(duration_s) FROM calls WHERE role='verify' AND {q}",
                        runs).fetchone()
        verified = sum(len(json.loads(r[0])) for r in con.execute(
            f"SELECT review_ids FROM calls WHERE role='verify' AND {q}", runs))
        fixed = con.execute(f"SELECT SUM(cost_usd) FROM calls WHERE role IN ('group','memo') AND {q}", runs).fetchone()[0]
        status = dict(con.execute("SELECT status, COUNT(*) FROM records GROUP BY status").fetchall())
        # Wall-clock throughput of the main enrichment run at its worker count.
        main_run = runs[-2] if len(runs) > 1 else runs[0]
        t = con.execute("SELECT COUNT(*), (julianday(MAX(started_at)) - julianday(MIN(started_at))) * 86400"
                        " FROM calls WHERE role='enrich' AND run_id=?", (main_run,)).fetchone()
        out[name] = {
            "runs": runs, "workers_main_run": workers, "rows": sum(status.values()), "record_status": status,
            "enrich_attempts": e[0], "enrich_failed_attempts": e[1], "distinct_texts_completed": sent,
            "enrich_cost_usd": round(e[5], 6), "enrich_cost_per_distinct_text": e[5] / sent,
            "output_tokens_per_text": e[4] / sent, "uncached_input_per_text": (e[2] - e[3]) / sent,
            "retry_rate": e[1] / max(1, e[0] - e[1]),
            "requests_per_second_main_run": t[0] / max(1, t[1]), "main_run": main_run,
            "verify_cost_per_review": (v[1] or 0) / max(1, verified), "fixed_group_memo_cost_usd": fixed or 0,
        }
    (HERE / "checkpoints.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
