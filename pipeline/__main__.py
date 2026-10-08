"""Pipeline orchestrator. Code controls the order, state, budgets and logs; models only do the
bounded language tasks inside enrich / verify / group-naming / memo.

Paid, explicit:
    uv run python -m pipeline run --input data/raw/cost_100.csv --state state/pilot.sqlite \
        --run-id pilot-cold --budget-usd 0.50

Offline (no API key, no model calls):
    uv run python -m pipeline rank --records runs/pilot-cold/records.jsonl \
        --membership runs/pilot-cold/membership.csv --out /tmp/rerank
"""

import argparse
import csv
import json
import time
from pathlib import Path

from pipeline import config as C
from pipeline import enrich, export, group, llm, memo, rank, verify
from pipeline.common import connect


def stage_cost(con, run_id, role):
    r = con.execute("SELECT COUNT(*), COALESCE(SUM(cost_usd),0), COALESCE(SUM(outcome='failed'),0) FROM calls"
                    " WHERE run_id=? AND role=?", (run_id, role)).fetchone()
    return {"calls": r[0], "failed_calls": r[2], "cost_usd": round(r[1], 6)}


def run_all(a):
    t0 = time.time()
    out = Path("runs") / a.run_id
    out.mkdir(parents=True, exist_ok=True)
    stages, stop = {}, None

    s = time.time()
    enrich_summary = enrich.run(a.input, a.state, a.run_id, a.phase, a.budget_usd, a.workers, C.ENRICH_BATCH_SIZE)
    stages["enrich"] = {"seconds": round(time.time() - s, 2), **{k: enrich_summary[k] for k in (
        "distinct_texts_to_call", "already_completed_same_config", "cache_hits_before_calls", "record_status",
        "stop_reason")}}
    if enrich_summary["stop_reason"]:
        stop = f"enrich: {enrich_summary['stop_reason']}"

    con = connect(a.state)
    client = llm.make_client()
    verify_report, issues, ranking, memo_result = {}, {}, [], None
    try:
        s = time.time()
        verify_report = verify.run(con, client, a.run_id, a.phase, a.budget_usd, out)
        stages["verify"] = {"seconds": round(time.time() - s, 2), "sampled": verify_report["sampled"],
                            "verified": verify_report["verified"]}

        s = time.time()
        records_counts = export.write_records(con, out / "records.jsonl")
        stages["export_records"] = {"seconds": round(time.time() - s, 2), "counts": records_counts}

        s = time.time()
        g = group.run(con, client, a.run_id, a.phase, a.budget_usd, out)
        stages["group"] = {"seconds": round(time.time() - s, 2), "issues": g["issues"], "members": g["members"]}

        s = time.time()
        ranking = rank.rank(out / "records.jsonl", out / "membership.csv")
        rank.write_ranking(ranking, out)
        stages["rank"] = {"seconds": round(time.time() - s, 2), "issues_ranked": len(ranking)}
        with (out / "issues.csv").open(encoding="utf-8") as f:
            issues = {r["issue_id"]: r for r in csv.DictReader(f)}

        s = time.time()
        memo_result = memo.run(con, client, a.run_id, a.phase, a.budget_usd, out, ranking, issues, verify_report,
                               records_counts)
        stages["memo"] = {"seconds": round(time.time() - s, 2), "check_passed": memo_result["check"]["passed"]}
    except llm.BudgetStop as e:
        stop = f"budget: {e}"
        print(f"  STOPPED by spending control: {e}")

    for role in ("enrich", "verify", "group", "memo"):
        stages.setdefault(role, {}).update(stage_cost(con, a.run_id, role))
    export.write_calls(con, out / "calls.jsonl", [a.run_id])
    total = round(sum(st.get("cost_usd", 0) for st in stages.values()), 6)
    summary = {"run_id": a.run_id, "phase": a.phase, "input": a.input, "state": a.state,
               "label_config": C.ENRICH_LABEL_CONFIG, "budget_usd": a.budget_usd, "workers": a.workers,
               "wall_clock_s": round(time.time() - t0, 2), "total_cost_usd": total, "stop_reason": stop,
               "stages": stages}
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[{a.run_id}] pipeline finished in {summary['wall_clock_s']}s | total ${total:.5f} | "
          + " | ".join(f"{r}: {stages[r]['calls']} calls" for r in ("enrich", "verify", "group", "memo"))
          + (f" | STOPPED: {stop}" if stop else ""))
    print(f"  outputs: {out}/")


def main():
    ap = argparse.ArgumentParser(prog="pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run all stages (makes paid API calls)")
    r.add_argument("--input", required=True)
    r.add_argument("--state", required=True)
    r.add_argument("--run-id", required=True)
    r.add_argument("--phase", default="initial", choices=["initial", "resume"])
    r.add_argument("--budget-usd", type=float, required=True)
    r.add_argument("--workers", type=int, default=1)
    c = sub.add_parser("checkpoint", help="snapshot the IDs of completed records (offline)")
    c.add_argument("--state", required=True)
    c.add_argument("--out", required=True)
    k = sub.add_parser("rank", help="regenerate ranking from saved files (offline)")
    k.add_argument("--records", required=True)
    k.add_argument("--membership", required=True)
    k.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        run_all(a)
    elif a.cmd == "checkpoint":
        con = connect(a.state)
        ids = [r[0] for r in con.execute("SELECT review_id FROM records WHERE status='completed' ORDER BY rowid")]
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"taken_at": llm.now(), "state": a.state, "completed_ids": ids}))
        print(f"Checkpoint: {len(ids):,} completed IDs saved to {a.out}")
    else:
        rows = rank.rank(a.records, a.membership)
        print(f"Wrote {rank.write_ranking(rows, a.out)} ({len(rows)} issues)")


if __name__ == "__main__":
    main()
