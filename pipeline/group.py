"""Stage 4 - Group. Code assigns every completed complaint/cancellation record to exactly one issue
(topic + keyword subtopic, see issue_rules.py). A small model then only NAMES each issue from a
bounded, deterministic set of example quotes. Membership never depends on the model."""

import csv
import hashlib
import json
from pathlib import Path

from pipeline import config as C
from pipeline import issue_rules, llm

PROMPT = (C.PROMPTS / f"{C.GROUP_PROMPT_VERSION}.txt").read_text()
GROUP_CONFIG = f"{C.GROUP_MODEL}+effort-{C.GROUP_EFFORT}+{C.GROUP_PROMPT_VERSION}+{issue_rules.RULES_VERSION}+examples-hash"
SCHEMA = {
    "type": "object",
    "properties": {"issues": {"type": "array", "items": {
        "type": "object",
        "properties": {"issue_id": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}},
        "required": ["issue_id", "name", "description"], "additionalProperties": False}}},
    "required": ["issues"], "additionalProperties": False,
}


def assign(con):
    """Return ({review_id: issue_id}, {review_id: row}) for all completed complaint/cancellation records."""
    membership, rows = {}, {}
    for r in con.execute("SELECT review_id, topic, severity, evidence_quote, review_text FROM records"
                         " WHERE status='completed' AND intent IN ('complaint','cancellation') ORDER BY rowid"):
        # The evidence quote is focused on the labelled problem; fall back to the full text.
        sub = issue_rules.subtopic(r["topic"], r["evidence_quote"])
        if sub == "general":
            sub = issue_rules.subtopic(r["topic"], r["review_text"])
        membership[r["review_id"]] = issue_rules.issue_id(r["topic"], sub)
        rows[r["review_id"]] = {"severity": r["severity"], "quote": r["evidence_quote"]}
    return membership, rows


def examples(rows, members, k):
    """Deterministic, bounded evidence: up to k distinct quotes per issue in pseudo-random (hash) order, so the
    examples are typical members. (v1 took the highest-severity members first; at full scale that surfaced rare
    extremes - e.g. duplicate charges - and the issue names described the extremes, not the typical complaint.)"""
    ordered = sorted(members, key=lambda i: hashlib.sha256(i.encode()).hexdigest())
    out, seen = [], set()
    for i in ordered:
        q = rows[i]["quote"][:200]
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append({"review_id": i, "quote": q})
        if len(out) == k:
            break
    return out


def run(con, client, run_id, phase, budget, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    membership, rows = assign(con)
    by_issue = {}
    for rid, iss in membership.items():
        by_issue.setdefault(iss, []).append(rid)

    with (out_dir / "membership.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue_id", "review_id"])
        for iss in sorted(by_issue):
            for rid in by_issue[iss]:
                w.writerow([iss, rid])

    pack = [{"issue_id": iss, "topic": iss.split("-")[1], "subtopic": iss.split("-", 2)[2],
             "examples": [e["quote"] for e in examples(rows, by_issue[iss], C.GROUP_EXAMPLES_PER_ISSUE)]}
            for iss in sorted(by_issue)]
    payload = json.dumps(pack, ensure_ascii=False)
    key = llm.input_hash("group", GROUP_CONFIG, payload)
    names = llm.get_artifact(con, key)
    calls = 0
    if names is None and pack:
        llm.reserve(con, run_id, budget, C.GROUP_MODEL, PROMPT, payload, 4000)
        for attempt in range(1, 3):
            started = llm.now()
            resp, err, secs = llm.call(client, model=C.GROUP_MODEL, effort=C.GROUP_EFFORT, instructions=PROMPT,
                                       payload=payload, max_output_tokens=4000 + 60 * len(pack),
                                       cache_key=C.GROUP_PROMPT_VERSION, schema=SCHEMA, schema_name="issue_names")
            calls += 1
            got = {}
            if resp is not None:
                try:
                    got = {i["issue_id"]: {"name": i["name"], "description": i["description"]}
                           for i in json.loads(resp.output_text)["issues"] if i["issue_id"] in by_issue}
                except Exception:
                    got = {}
            ok = set(got) == set(by_issue)  # reject unknown ids; require every issue
            llm.log_call(con, run_id=run_id, role="group", phase=phase, model=C.GROUP_MODEL, effort=C.GROUP_EFFORT,
                         config=GROUP_CONFIG, batch_no=1, attempt=attempt, review_ids=[], resp=resp,
                         error=err or (None if ok else "missing_or_unknown_issue_ids"), ok=ok, n_valid=len(got),
                         seconds=secs, started=started)
            if ok:
                names = got
                llm.put_artifact(con, key, "group", GROUP_CONFIG, names)
                break
            if err is not None and llm.is_fatal(err):
                break
    if names is None:  # deterministic fallback: still a complete, usable issue table
        names = {iss: {"name": iss.split("-", 1)[1].replace("-", ": ").replace("_", " "),
                       "description": "(name not generated)"} for iss in by_issue}

    with (out_dir / "issues.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["issue_id", "topic", "subtopic", "name", "description", "member_count", "example_review_ids"])
        for p in pack:
            iss = p["issue_id"]
            w.writerow([iss, p["topic"], p["subtopic"], names[iss]["name"], names[iss]["description"],
                        len(by_issue[iss]),
                        " ".join(e["review_id"] for e in examples(rows, by_issue[iss], C.GROUP_EXAMPLES_PER_ISSUE))])
    print(f"  group: {len(membership)} complaint/cancellation records -> {len(by_issue)} issues, {calls} new calls")
    return {"issues": len(by_issue), "members": len(membership), "new_model_calls": calls, "config": GROUP_CONFIG,
            "names": names}
