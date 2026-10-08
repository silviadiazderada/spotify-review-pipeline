"""Stage 5 - Rank (code only, no model). Reproducible from saved files:

    uv run python -m pipeline.rank --records out/records.jsonl --membership out/membership.csv --out out/

priority(issue) = complaint_count x mean_severity = severity_sum (exact integer, no rounding loss).
Order: descending score, then ascending issue_id. Means: 6 decimals, decimal half-up.
"""

import argparse
import csv
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

COUNTED_INTENTS = ("complaint", "cancellation")


def mean6(total, n):
    return str((Decimal(total) / Decimal(n)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def rank(records_path, membership_path):
    records = {}
    with Path(records_path).open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["status"] == "completed" and r["intent"] in COUNTED_INTENTS:
                records[r["review_id"]] = r
    pairs = set()
    with Path(membership_path).open(encoding="utf-8", newline="") as f:
        for m in csv.DictReader(f):
            if m["review_id"] not in records:
                raise ValueError(f"membership references a non-complaint or unknown record: {m['review_id']}")
            pairs.add((m["issue_id"], m["review_id"]))  # each review counted once per issue
    unassigned = set(records) - {rid for _, rid in pairs}
    if unassigned:
        raise ValueError(f"{len(unassigned)} complaint/cancellation records belong to no issue")

    agg = {}
    for issue, rid in pairs:
        a = agg.setdefault(issue, {"complaint_count": 0, "severity_sum": 0})
        a["complaint_count"] += 1
        a["severity_sum"] += int(records[rid]["severity"])
    ordered = sorted(agg.items(), key=lambda kv: (-kv[1]["severity_sum"], kv[0]))
    return [{"rank": i, "issue_id": issue, "complaint_count": a["complaint_count"], "severity_sum": a["severity_sum"],
             "mean_severity": mean6(a["severity_sum"], a["complaint_count"]), "priority_score": a["severity_sum"]}
            for i, (issue, a) in enumerate(ordered, start=1)]


def write_ranking(rows, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "ranking.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity",
                                          "priority_score"])
        w.writeheader()
        w.writerows({k: str(v) for k, v in r.items()} for r in rows)
    return out_dir / "ranking.csv"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Regenerate the baseline ranking from saved outputs (no model calls).")
    ap.add_argument("--records", required=True)
    ap.add_argument("--membership", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = rank(a.records, a.membership)
    print(f"Wrote {write_ranking(rows, a.out)} ({len(rows)} issues)")
    for r in rows[:10]:
        print(f"  {r['rank']:>2}. {r['issue_id']:<45} count {r['complaint_count']:>6}  mean {r['mean_severity']}  "
              f"score {r['priority_score']}")
