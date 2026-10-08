"""Trace one real review through every stage, from saved outputs only (no model calls).

    uv run python scripts/trace_review.py --state state/full.sqlite --outputs runs/full-final [--review-id ID]

Without --review-id it picks a review that was (a) labelled by its own model call, (b) in the verifier
sample, (c) a member of the top-ranked issue in a decision area, and (d) cited in the memo evidence if possible.
"""

import argparse
import csv
import json
import sqlite3
from pathlib import Path


def main(state, outputs, review_id=None):
    out = Path(outputs)
    con = sqlite3.connect(state)
    con.row_factory = sqlite3.Row
    membership = {m["review_id"]: m["issue_id"] for m in csv.DictReader((out / "membership.csv").open())}
    ranking = {r["issue_id"]: r for r in csv.DictReader((out / "ranking.csv").open())}
    claims = [c for c in csv.DictReader((out / "claims.csv").open())]
    verify = {v["review_id"]: v for v in csv.DictReader((out / "verify_comparisons.csv").open(encoding="utf-8"))}
    memo = (out / "memo.md").read_text()

    if review_id is None:
        claimed = {c["issue_id"] for c in claims}
        cands = [rid for rid, v in verify.items() if v["status"] == "verified" and rid in membership
                 and membership[rid] in claimed and not membership[rid].startswith("ISS-other")]
        cited = [rid for rid in cands if rid in memo]
        review_id = (cited or sorted(cands, key=lambda r: int(ranking[membership[r]]["rank"])))[0]

    r = con.execute("SELECT * FROM records WHERE review_id=?", (review_id,)).fetchone()
    call = con.execute("SELECT c.request_id, c.run_id, c.phase, c.model, c.effort, c.batch_no, c.attempt, c.input_tokens,"
                       " c.output_tokens FROM calls c, json_each(c.review_ids) j WHERE c.role='enrich' AND"
                       " c.outcome='succeeded' AND j.value=?", (r["cache_source_id"] or review_id,)).fetchone()
    issue = membership.get(review_id)
    rk = ranking.get(issue, {})
    v = verify.get(review_id)
    issue_claims = [c for c in claims if c["issue_id"] == issue]
    lines = [
        f"**1. Source.** Review `{review_id}` ({r['review_rating']}★, {r['review_timestamp']}, app {r['app_version'] or 'unknown'}). "
        f"Source-row hash `{r['source_sha256'][:16]}…`. Text: “{r['review_text'][:300]}”",
        f"**2. Enrich** (`{r['label_config']}`). Request `{call['request_id']}` in run `{call['run_id']}` (phase "
        f"{call['phase']}, batch {call['batch_no']}, attempt {call['attempt']}). Result: intent **{r['intent']}**, "
        f"topic **{r['topic']}**, severity **{r['severity']}**, sentiment {r['sentiment']}, needs_review "
        f"{bool(r['needs_review'])}. Evidence quote: “{r['evidence_quote']}” (exact substring: "
        f"{r['evidence_quote'] in r['review_text']}).",
        (f"**3. Verify** (independent, no access to step 2). Verifier said intent **{v['verify_intent']}**, topic "
         f"**{v['verify_topic']}**, severity **{v['verify_severity']}**. Agreement: intent {v['intent_agree']}, topic "
         f"{v['topic_agree']}, severity {v['severity_agree']}.") if v else "**3. Verify.** Not in the declared sample.",
        f"**4. Group.** Code rule assigned issue `{issue}` (`membership.csv`).",
        f"**5. Rank.** `{issue}` is rank {rk.get('rank')}: complaint_count {rk.get('complaint_count')}, severity_sum "
        f"{rk.get('severity_sum')}, mean_severity {rk.get('mean_severity')}, priority_score {rk.get('priority_score')}.",
        "**6. Memo.** Claims for this issue: " + (", ".join(f"`{c['claim_id']}` {c['metric']}={c['value']}" for c in issue_claims)
                                              or "none (issue not in the memo's top issues)")
        + (". This review is quoted in the memo." if review_id in memo else "."),
    ]
    print("\n\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outputs", required=True)
    ap.add_argument("--review-id")
    a = ap.parse_args()
    main(a.state, a.outputs, a.review_id)
