"""Copy the real pilot evidence from the state database and run folders into cost/ (no model calls).

    uv run python cost/collect.py
"""

import csv
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from pipeline import config as C  # noqa: E402
from pipeline.export import write_calls  # noqa: E402

A = json.loads((HERE / "assumptions.json").read_text())
RUNS = [A["cold_run_id"], A["warm_run_id"]]


def main():
    con = sqlite3.connect(ROOT / "state" / "pilot.sqlite")
    con.row_factory = sqlite3.Row

    n = write_calls(con, HERE / "pilot_calls.jsonl", RUNS)

    # One result/status per pilot ID, in the grading contract's record format.
    src = ROOT / "runs" / A["cold_run_id"] / "records.jsonl"
    (HERE / "pilot_records.jsonl").write_text(src.read_text())

    runs = {}
    for run_id in RUNS:
        s = json.loads((ROOT / "runs" / run_id / "run_summary.json").read_text())
        e = json.loads((ROOT / "runs" / run_id / "enrich_summary.json").read_text())
        st = s["stages"]
        runs[run_id] = {
            "input_sha256": e["input_sha256"], "workers": s["workers"], "wall_clock_s": s["wall_clock_s"],
            "stage_seconds": {r: st[r].get("seconds") for r in ("enrich", "verify", "group", "memo")},
            "rows": e["ingest"]["rows"], "completed": e["record_status"].get("completed", 0),
            "failed_records": e["ingest"]["rows"] - e["record_status"].get("completed", 0),
            "already_completed": e["already_completed_same_config"], "cache_hits": e["cache_hits_before_calls"],
            "unique_texts": len({r[0] for r in con.execute("SELECT text_sha256 FROM records")}),
            "models": {"enrich": C.ENRICH_MODEL, "verify": C.VERIFY_MODEL, "group": C.GROUP_MODEL, "memo": C.MEMO_MODEL},
            "efforts": {"enrich": C.ENRICH_EFFORT, "verify": C.VERIFY_EFFORT, "group": C.GROUP_EFFORT,
                        "memo": C.MEMO_EFFORT},
            "provider_reported_cost_usd": s["total_cost_usd"],
        }
    (HERE / "pilot_runs.json").write_text(json.dumps(runs, indent=2))

    # usage.csv: every charged item mapped to its call (request_id).
    with (HERE / "usage.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["request_id", "run_id", "role", "model", "billing_item", "billed_units", "unit",
                    "reasoning_tokens_included_in_output"])
        for line in (HERE / "pilot_calls.jsonl").read_text().splitlines():
            c = json.loads(line)
            cached = c["cached_input_tokens"] or 0
            for item, units in (("input_uncached", (c["input_tokens"] or 0) - cached), ("input_cached", cached),
                                ("output", c["output_tokens"] or 0)):
                w.writerow([c["request_id"], c["run_id"], c["role"], c["model"], item, units, "tokens",
                            c["reasoning_tokens"] if item == "output" else ""])
    print(f"Collected {n} calls for runs {RUNS} into {HERE}")


if __name__ == "__main__":
    main()
