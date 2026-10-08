"""Write records.jsonl in the grading-contract format: exactly one final record per source ID.
Pending rows (never classified) are exported as quarantined with an explicit reason - they are
accounted for, but they are not successful classifications."""

import json
from pathlib import Path


def record_json(r):
    if r["status"] == "completed":
        out = {
            "review_id": r["review_id"], "source_sha256": r["source_sha256"], "status": "completed",
            "topic": r["topic"], "intent": r["intent"], "sentiment": r["sentiment"], "severity": r["severity"],
            "entities": json.loads(r["entities"] or "[]"), "evidence_quote": r["evidence_quote"],
            "needs_review": bool(r["needs_review"]), "label_config": r["label_config"],
        }
        if r["cache_source_id"]:
            out["cache_source_id"] = r["cache_source_id"]
        return out
    reason = r["reason"] if r["status"] == "quarantined" else "pending_not_classified"
    return {"review_id": r["review_id"], "source_sha256": r["source_sha256"], "status": "quarantined", "reason": reason}


def write_records(con, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    with path.open("w", encoding="utf-8") as f:
        for r in con.execute("SELECT * FROM records ORDER BY rowid"):
            rec = record_json(r)
            key = rec["status"] if rec["status"] == "completed" else f"quarantined:{rec['reason']}"
            counts[key] = counts.get(key, 0) + 1
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return counts


def write_calls(con, path, run_ids=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    q = "SELECT * FROM calls" + (f" WHERE run_id IN ({','.join('?' * len(run_ids))})" if run_ids else "") + " ORDER BY call_id"
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for c in con.execute(q, run_ids or []):
            f.write(json.dumps({
                "request_id": c["request_id"], "run_id": c["run_id"], "role": c["role"],
                "review_ids": json.loads(c["review_ids"] or "[]"), "model": c["model"], "effort": c["effort"],
                "phase": c["phase"], "outcome": c["outcome"], "label_config": c["label_config"],
                "batch_no": c["batch_no"], "attempt": c["attempt"], "error": c["error"],
                "input_tokens": c["input_tokens"], "cached_input_tokens": c["cached_tokens"],
                "output_tokens": c["output_tokens"], "reasoning_tokens": c["reasoning_tokens"],
                "cost_usd": round(c["cost_usd"] or 0, 8), "started_at": c["started_at"], "duration_s": c["duration_s"],
            }) + "\n")
            n += 1
    return n
