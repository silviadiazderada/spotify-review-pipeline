"""Stage 3 - Verify: an independent model task re-labels a declared random sample WITHOUT seeing the
enricher's answer. Code then compares the two and writes a disagreement report.

The sample is deterministic: distinct completed texts sorted by sha256(seed + review_id).
"""

import csv
import hashlib
import json
import math
import time
from collections import Counter
from pathlib import Path

from pipeline import config as C
from pipeline import llm

PROMPT = (C.PROMPTS / f"{C.VERIFY_PROMPT_VERSION}.txt").read_text()
ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "intent": {"type": "string", "enum": C.INTENTS},
        "topic": {"type": "string", "enum": C.TOPICS},
        "severity": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
    },
    "required": ["id", "intent", "topic", "severity"],
    "additionalProperties": False,
}
SCHEMA = {"type": "object", "properties": {"results": {"type": "array", "items": ITEM}},
          "required": ["results"], "additionalProperties": False}
FIELDS = ("intent", "topic", "severity")


def sample(con):
    """Representative records only (cache_source_id IS NULL): one per distinct text."""
    rows = con.execute(
        "SELECT review_id, text_sha256, review_text, intent, topic, severity FROM records"
        " WHERE status='completed' AND label_config=? AND cache_source_id IS NULL", (C.ENRICH_LABEL_CONFIG,)).fetchall()
    n = min(len(rows), C.VERIFY_MAX, max(C.VERIFY_MIN, math.ceil(C.VERIFY_RATE * len(rows))))
    key = lambda r: hashlib.sha256(f"{C.VERIFY_SEED}:{r['review_id']}".encode()).hexdigest()
    return sorted(rows, key=key)[:n], len(rows)


def label_texts(con, client, run_id, phase, budget, items, batch_size=50):
    """items: list of (review_id, text_sha, text). Returns {text_sha: labels}; uses and fills the verifier cache."""
    found = {}
    todo = []
    for rid, tsha, text in items:
        row = con.execute("SELECT labels FROM verify_results WHERE text_sha256=? AND verify_config=?",
                          (tsha, C.VERIFY_CONFIG)).fetchone()
        if row:
            found[tsha] = json.loads(row["labels"])
        else:
            todo.append((rid, tsha, text))
    calls = 0
    for b, start in enumerate(range(0, len(todo), batch_size), start=1):
        batch = todo[start:start + batch_size]
        for attempt in range(1, C.MAX_API_ATTEMPTS + 1):
            short = {f"v{i}": item for i, item in enumerate(batch, start=1)}
            payload = json.dumps([{"id": s, "text": t} for s, (_, _, t) in short.items()], ensure_ascii=False)
            llm.reserve(con, run_id, budget, C.VERIFY_MODEL, PROMPT, payload, C.VERIFY_MAX_OUTPUT_TOKENS)
            started = llm.now()
            resp, err, secs = llm.call(client, model=C.VERIFY_MODEL, effort=C.VERIFY_EFFORT, instructions=PROMPT,
                                       payload=payload, max_output_tokens=C.VERIFY_MAX_OUTPUT_TOKENS,
                                       cache_key=C.VERIFY_PROMPT_VERSION, schema=SCHEMA, schema_name="verify_labels")
            calls += 1
            valid = {}
            if resp is not None:
                try:
                    for r in json.loads(resp.output_text)["results"]:
                        if r.get("id") in short and r["id"] not in valid:
                            valid[r["id"]] = {k: r[k] for k in FIELDS}
                except Exception:
                    pass
            llm.log_call(con, run_id=run_id, role="verify", phase=phase, model=C.VERIFY_MODEL, effort=C.VERIFY_EFFORT,
                         config=C.VERIFY_CONFIG, batch_no=b, attempt=attempt, review_ids=[x[0] for x in batch],
                         resp=resp, error=err or (None if len(valid) == len(batch) else "missing_items"),
                         ok=len(valid) == len(batch), n_valid=len(valid), seconds=secs, started=started)
            with con:
                for s, labels in valid.items():
                    rid, tsha, _ = short[s]
                    con.execute("INSERT OR REPLACE INTO verify_results VALUES (?,?,?,?)",
                                (tsha, C.VERIFY_CONFIG, rid, json.dumps(labels)))
                    found[tsha] = labels
            batch = [x for s, x in short.items() if s not in valid]
            if not batch or (err is not None and llm.is_fatal(err)):
                break
            if err is not None:
                time.sleep(min(30, 2 ** attempt))
    return found, calls


def run(con, client, run_id, phase, budget, out_dir):
    chosen, population = sample(con)
    verdicts, calls = label_texts(con, client, run_id, phase, budget,
                                  [(r["review_id"], r["text_sha256"], r["review_text"]) for r in chosen])
    rows, agree = [], Counter()
    for r in chosen:
        v = verdicts.get(r["text_sha256"])
        if v is None:
            rows.append({"review_id": r["review_id"], "status": "not_verified"})
            continue
        row = {"review_id": r["review_id"], "status": "verified", "review_text": r["review_text"]}
        for f in FIELDS:
            row[f"enrich_{f}"], row[f"verify_{f}"] = r[f], v[f]
            row[f"{f}_agree"] = r[f] == v[f]
            agree[f] += row[f"{f}_agree"]
        row["severity_abs_diff"] = abs(r["severity"] - v["severity"])
        rows.append(row)

    verified = [r for r in rows if r["status"] == "verified"]
    n = len(verified)
    report = {
        "verify_config": C.VERIFY_CONFIG, "enrich_config": C.ENRICH_LABEL_CONFIG,
        "sample_rule": f"{C.VERIFY_RATE:.0%} of distinct completed texts (min {C.VERIFY_MIN}, max {C.VERIFY_MAX}), "
                       f"ordered by sha256('{C.VERIFY_SEED}:' + review_id)",
        "population_distinct_texts": population, "sampled": len(chosen), "verified": n, "new_model_calls": calls,
        "agreement": {f: round(agree[f] / n, 4) if n else None for f in FIELDS},
        "severity_mae": round(sum(r["severity_abs_diff"] for r in verified) / n, 4) if n else None,
        "disagreements": sum(1 for r in verified if not all(r[f"{f}_agree"] for f in FIELDS)),
        "intent_confusion": Counter(f"{r['enrich_intent']}->{r['verify_intent']}" for r in verified
                                    if not r["intent_agree"]).most_common(),
        "topic_confusion": Counter(f"{r['enrich_topic']}->{r['verify_topic']}" for r in verified
                                   if not r["topic_agree"]).most_common(),
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "verify_report.json").write_text(json.dumps(report, indent=2))
    with (out_dir / "verify_comparisons.csv").open("w", newline="", encoding="utf-8") as f:
        cols = ["review_id", "status"] + [f"{p}_{f}" for f in FIELDS for p in ("enrich", "verify")] + \
               [f"{f}_agree" for f in FIELDS] + ["severity_abs_diff", "review_text"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  verify: {n}/{len(chosen)} sampled texts verified, {calls} new calls | agreement "
          + ", ".join(f"{f} {report['agreement'][f]}" for f in FIELDS) + f" | severity MAE {report['severity_mae']}")
    return report
