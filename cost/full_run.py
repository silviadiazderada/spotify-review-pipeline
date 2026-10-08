"""Summarize the ACTUAL full-run usage and cost from the saved call log (no model calls).

    uv run python cost/full_run.py     # writes cost/full_run_actual.json (read by cost/calculator.py)
"""

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
con = sqlite3.connect(HERE.parent / "state" / "full.sqlite")
rows = con.execute(
    "SELECT role, COUNT(*), SUM(outcome='failed'), SUM(input_tokens), SUM(cached_tokens), SUM(output_tokens),"
    " SUM(reasoning_tokens), SUM(cost_usd) FROM calls GROUP BY role").fetchall()
runs = con.execute(
    "SELECT run_id, phase, MIN(started_at), MAX(started_at), COUNT(*), SUM(cost_usd) FROM calls GROUP BY run_id"
    " ORDER BY MIN(call_id)").fetchall()
status = dict(con.execute("SELECT status, COUNT(*) FROM records GROUP BY status").fetchall())
out = {
    "record_status": status,
    "by_role": {r[0]: {"calls": r[1], "failed": r[2], "input_tokens": r[3], "cached_input_tokens": r[4],
                       "output_tokens": r[5], "reasoning_tokens": r[6], "cost_usd": round(r[7], 4)} for r in rows},
    "by_run": [{"run_id": r[0], "phase": r[1], "first_call": r[2], "last_call": r[3], "calls": r[4],
                "cost_usd": round(r[5], 4)} for r in runs],
    "total_cost_usd": round(sum(r[7] for r in rows), 4),
    "notes": ["Costs = provider-reported usage x standard rates in rates.csv; failed calls refused for "
              "insufficient_quota reported 0 tokens.",
              "Up to 16 in-flight requests were abandoned at each of 3 interruptions; their charges are not in the "
              "log (estimated at most ~$0.02 each) - reconcile with the provider usage page.",
              "Wall-clock is not a clean measurement: the run spanned an on-camera interruption, an overnight "
              "slowdown from a database query-plan bug (fixed), and a pause when prepaid credit ran out."],
}
(HERE / "full_run_actual.json").write_text(json.dumps(out, indent=2))
print(json.dumps({k: out[k] for k in ("record_status", "total_cost_usd")}), json.dumps(out["by_role"], indent=0))
