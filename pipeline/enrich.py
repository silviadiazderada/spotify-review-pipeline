"""Stage 2 - Enrich: label each distinct review text with topic, intent, severity, sentiment,
evidence quote, entities and needs_review.

Code owns: reading rows, hashing, the result cache, batching (<= 50 per request), validating
every returned id and field, retries, the spend ledger, saving after each batch, and resume.
The model owns: reading the language and choosing labels.

Usage (makes paid API calls - this is the explicit execution command):
    uv run python -m pipeline.enrich --input data/raw/cost_100.csv --db state/pilot.sqlite \
        --run-id pilot-cold --budget-usd 0.50
"""

import argparse
import json
import random
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from pipeline import config as C
from pipeline.common import connect, csv_rows, file_sha, row_sha, text_sha

PROMPT = (C.PROMPTS / f"{C.ENRICH_PROMPT_VERSION}.txt").read_text()

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "intent": {"type": "string", "enum": C.INTENTS},
        "topic": {"type": "string", "enum": C.TOPICS},
        "severity": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "sentiment": {"type": "number", "enum": C.SENTIMENTS},
        "evidence_quote": {"type": "string"},
        "entities": {"type": "array", "items": {"type": "string"}},
        "needs_review": {"type": "boolean"},
    },
    "required": ["id", "intent", "topic", "severity", "sentiment", "evidence_quote", "entities", "needs_review"],
    "additionalProperties": False,
}
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": ITEM_SCHEMA}},
    "required": ["results"],
    "additionalProperties": False,
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------------------
# 1. Ingest: register every source row (no model)
# ---------------------------------------------------------------------------
def ingest(con, input_path, run_id):
    counts = {"rows": 0, "new": 0, "empty_quarantined": 0}
    with con:
        for row in csv_rows(input_path):
            counts["rows"] += 1
            rid, digest, text = row["review_id"], row_sha(row), row["review_text"]
            meta = (row["review_rating"], row["review_likes"], row["app_version"], row["review_timestamp"], rid)
            existing = con.execute("SELECT source_sha256 FROM records WHERE review_id=?", (rid,)).fetchone()
            if existing:
                if existing["source_sha256"] != digest:
                    raise ValueError(f"Source row changed for {rid}; refusing to mix inputs in one state DB")
                con.execute("UPDATE records SET review_rating=?, review_likes=?, app_version=?, review_timestamp=?"
                            " WHERE review_id=? AND review_timestamp IS NULL", meta)
                continue
            counts["new"] += 1
            if not text.strip():
                counts["empty_quarantined"] += 1
                con.execute(
                    "INSERT INTO records(review_id, source_sha256, review_text, status, reason, run_id, updated_at)"
                    " VALUES (?,?,?,?,?,?,?)", (rid, digest, text, "quarantined", "empty_review_text", run_id, now()))
                con.execute("UPDATE records SET review_rating=?, review_likes=?, app_version=?, review_timestamp=?"
                            " WHERE review_id=?", meta)
            else:
                con.execute(
                    "INSERT INTO records(review_id, source_sha256, text_sha256, review_text, status, run_id, updated_at)"
                    " VALUES (?,?,?,?,?,?,?)", (rid, digest, text_sha(text), text, "pending", run_id, now()))
                con.execute("UPDATE records SET review_rating=?, review_likes=?, app_version=?, review_timestamp=?"
                            " WHERE review_id=?", meta)
    return counts


# ---------------------------------------------------------------------------
# 2. Result cache: reuse a validated answer for identical text + identical config
# ---------------------------------------------------------------------------
def apply_cache(con, run_id):
    rows = con.execute(
        "SELECT r.review_id, res.source_review_id, res.labels FROM records r JOIN results res"
        " ON res.text_sha256=r.text_sha256 AND res.label_config=?"
        " WHERE r.status='pending'", (C.ENRICH_LABEL_CONFIG,)).fetchall()
    with con:
        for r in rows:
            src = r["source_review_id"]
            complete_record(con, r["review_id"], json.loads(r["labels"]), run_id,
                            cache_source_id=None if src == r["review_id"] else src)
    return len(rows)


def complete_record(con, review_id, labels, run_id, cache_source_id=None, attempts=None):
    con.execute(
        "UPDATE records SET status='completed', reason=NULL, label_config=?, cache_source_id=?, topic=?, intent=?,"
        " sentiment=?, severity=?, entities=?, evidence_quote=?, needs_review=?, quote_fallback=?,"
        " attempts=COALESCE(?, attempts), run_id=?, updated_at=? WHERE review_id=?",
        (C.ENRICH_LABEL_CONFIG, cache_source_id, labels["topic"], labels["intent"], labels["sentiment"],
         labels["severity"], json.dumps(labels["entities"], ensure_ascii=False), labels["evidence_quote"],
         int(labels["needs_review"]), int(labels["quote_fallback"]), attempts, run_id, now(), review_id))


# ---------------------------------------------------------------------------
# 3. Model call (runs in a worker thread; no database access here)
# ---------------------------------------------------------------------------
def output_cap(n_items):
    """Bounded output: ~120 tokens per review (measured average ~45) plus overhead, never above the global cap.
    Limits the cost of a degenerate (looping) response."""
    return min(C.ENRICH_MAX_OUTPUT_TOKENS, 300 + 120 * n_items)


def call_model(client, items):
    """items: list of (short_id, text). Returns (response | None, error | None, seconds)."""
    payload = json.dumps([{"id": sid, "text": text} for sid, text in items], ensure_ascii=False)
    t0 = time.time()
    try:
        resp = client.responses.create(
            model=C.ENRICH_MODEL,
            reasoning={"effort": C.ENRICH_EFFORT},
            instructions=PROMPT,                       # identical prefix every call -> provider prompt cache
            input=payload,
            text={"format": {"type": "json_schema", "name": "review_labels", "schema": RESPONSE_SCHEMA, "strict": True}},
            max_output_tokens=output_cap(len(items)),
            prompt_cache_key=C.ENRICH_PROMPT_VERSION,
            store=False,
        )
        return resp, None, time.time() - t0
    except Exception as e:  # recorded as a failed attempt; the orchestrator decides what to do next
        return None, e, time.time() - t0


def validate(resp, items):
    """Return {short_id: labels} for every valid item; anything missing or invalid is simply absent."""
    texts = dict(items)
    try:
        data = json.loads(resp.output_text)
        results = data["results"]
    except Exception:
        return {}
    valid = {}
    for r in results:
        sid = r.get("id")
        if sid not in texts or sid in valid:
            continue  # unknown or duplicated id: rejected
        if r.get("intent") not in C.INTENTS or r.get("topic") not in C.TOPICS:
            continue
        if r.get("severity") not in (1, 2, 3, 4, 5) or r.get("sentiment") not in C.SENTIMENTS:
            continue
        quote = r.get("evidence_quote") or ""
        fallback = not quote or quote not in texts[sid]
        valid[sid] = {
            "topic": r["topic"], "intent": r["intent"], "severity": r["severity"],
            "sentiment": float(r["sentiment"]),
            # Exact-substring rule enforced in code: an unmatched quote is replaced by the full text.
            "evidence_quote": texts[sid] if fallback else quote,
            "quote_fallback": fallback,
            "entities": [e for e in r.get("entities", []) if isinstance(e, str)][:3],
            "needs_review": bool(r.get("needs_review")),
        }
    return valid


# ---------------------------------------------------------------------------
# 4. Orchestrator
# ---------------------------------------------------------------------------
class Ledger:
    """Spend control: reserve worst-case cost before dispatch; stop when spent + reserved would exceed the cap."""

    def __init__(self, budget):
        self.budget, self.spent, self.reserved = budget, 0.0, 0.0

    @staticmethod
    def worst_case(items):
        est_input = (len(PROMPT) + sum(len(t) for _, t in items) + 40 * len(items)) / 3  # generous chars->tokens
        return C.call_cost(C.ENRICH_MODEL, int(est_input), 0, output_cap(len(items)))

    def try_reserve(self, amount):
        if self.spent + self.reserved + amount > self.budget:
            return False
        self.reserved += amount
        return True

    def settle(self, reserved, actual):
        self.reserved -= reserved
        self.spent += actual


def log_call(con, run_id, phase, batch_no, attempt, review_ids, resp, error, n_valid, seconds, started):
    usage = getattr(resp, "usage", None)
    inp = getattr(usage, "input_tokens", 0) or 0
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    reasoning = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", 0) or 0
    cost = C.call_cost(C.ENRICH_MODEL, inp, cached, out)
    outcome = "succeeded" if resp is not None and n_valid == len(review_ids) else "failed"
    if error is None and resp is not None and n_valid < len(review_ids):
        error = f"invalid_or_missing_items: {len(review_ids) - n_valid} of {len(review_ids)} (status={resp.status})"
    con.execute(
        "INSERT INTO calls(request_id, run_id, role, phase, model, effort, label_config, batch_no, attempt, review_ids,"
        " outcome, error, n_valid, input_tokens, cached_tokens, output_tokens, reasoning_tokens, cost_usd, started_at,"
        " duration_s) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (getattr(resp, "id", None) or f"local-{run_id}-{batch_no}-{attempt}", run_id, "enrich", phase, C.ENRICH_MODEL,
         C.ENRICH_EFFORT, C.ENRICH_LABEL_CONFIG, batch_no, attempt, json.dumps(review_ids), outcome,
         None if error is None else f"{type(error).__name__}: {error}"[:500] if isinstance(error, Exception) else error,
         n_valid, inp, cached, out, reasoning, cost, started, round(seconds, 3)))
    return cost


def is_fatal(error):
    """Errors where retrying cannot help: bad key, no quota/spend limit reached, invalid request."""
    status = getattr(error, "status_code", None)
    # "No credits" arrives as a 429 like a rate limit, but retrying cannot help: stop and keep records pending.
    quota = "insufficient_quota" in f"{getattr(error, 'code', '')} {error}"
    return status in (400, 401, 403, 404) or quota


def requeue_quarantined(con, run_id):
    """Explicit, logged operator action: give model-output quarantines another pass under fixed code.
    Empty-text quarantines are never requeued."""
    with con:
        n = con.execute("UPDATE records SET status='pending', reason=NULL, run_id=?, updated_at=? WHERE status='quarantined'"
                        " AND reason!='empty_review_text'", (run_id, now())).rowcount
    return n


def run(input_path, db_path, run_id, phase, budget, workers, batch_size, limit=None, requeue=False):
    from openai import OpenAI  # imported here so offline commands never need the SDK or a key

    load_dotenv()
    client = OpenAI(max_retries=0, timeout=120)
    con = connect(db_path)
    t_start = time.time()
    summary = {"run_id": run_id, "phase": phase, "input": str(input_path), "input_sha256": file_sha(input_path),
               "label_config": C.ENRICH_LABEL_CONFIG, "batch_size": batch_size, "workers": workers,
               "budget_usd": budget, "started_at": now()}

    summary["ingest"] = ingest(con, input_path, run_id)
    summary["requeued_quarantined"] = requeue_quarantined(con, run_id) if requeue else 0
    summary["already_completed_same_config"] = con.execute(
        "SELECT COUNT(*) FROM records WHERE status='completed' AND label_config=?", (C.ENRICH_LABEL_CONFIG,)).fetchone()[0]
    summary["cache_hits_before_calls"] = apply_cache(con, run_id)

    # One representative per distinct pending text; duplicates inherit its result.
    pending = con.execute(
        "SELECT text_sha256, MIN(review_id) AS rep, review_text FROM records WHERE status='pending'"
        " GROUP BY text_sha256 ORDER BY MIN(rowid)").fetchall()
    if limit:
        pending = pending[:limit]
    queue = [(p["text_sha256"], p["rep"], p["review_text"]) for p in pending]
    batches = [queue[i:i + batch_size] for i in range(0, len(queue), batch_size)]
    summary["distinct_texts_to_call"] = len(queue)
    print(f"[{run_id}] {summary['ingest']['rows']} rows | already done {summary['already_completed_same_config']} | cache hits {summary['cache_hits_before_calls']} | "
          f"{len(queue)} distinct texts to label in {len(batches)} requests | budget ${budget:.2f}")

    ledger = Ledger(budget)
    stop_reason = None
    # work item: (batch_no, attempt, [(text_sha, rep_id, text)], invalid_retries_used)
    todo = [(n, 1, b, 0) for n, b in enumerate(batches, start=1)]
    in_flight = {}

    def finish_batch(batch_no, attempt, batch, valid_by_rep):
        with con:
            for tsha, rep, _ in batch:
                labels = valid_by_rep.get(rep)
                if labels is None:
                    continue
                con.execute("INSERT OR REPLACE INTO results(text_sha256, label_config, source_review_id, labels)"
                            " VALUES (?,?,?,?)", (tsha, C.ENRICH_LABEL_CONFIG, rep, json.dumps(labels, ensure_ascii=False)))
                for r in con.execute("SELECT review_id FROM records WHERE text_sha256=? AND status='pending'", (tsha,)).fetchall():
                    complete_record(con, r["review_id"], labels, run_id,
                                    cache_source_id=None if r["review_id"] == rep else rep, attempts=attempt)

    def quarantine(batch, reason, attempts):
        with con:
            for tsha, _, _ in batch:
                con.execute("UPDATE records SET status='quarantined', reason=?, attempts=?, run_id=?, updated_at=?"
                            " WHERE text_sha256=? AND status='pending'", (reason, attempts, run_id, now(), tsha))

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while todo or in_flight:
                # Dispatch while we have free workers and budget.
                while todo and len(in_flight) < workers and not stop_reason:
                    batch_no, attempt, batch, inv = todo[0]
                    items = [(f"r{i}", text) for i, (_, _, text) in enumerate(batch, start=1)]
                    reserve = Ledger.worst_case(items)
                    if not ledger.try_reserve(reserve):
                        stop_reason = (f"budget: spent ${ledger.spent:.4f} + reserved ${ledger.reserved:.4f} + next "
                                       f"${reserve:.4f} > cap ${budget:.2f}")
                        break
                    todo.pop(0)
                    fut = pool.submit(call_model, client, items)
                    in_flight[fut] = (batch_no, attempt, batch, inv, items, reserve, now())
                if not in_flight:
                    break

                try:
                    done, _ = wait(in_flight, return_when=FIRST_COMPLETED)
                except KeyboardInterrupt:
                    # Graceful stop: no new dispatches; requests already in flight are still collected and saved.
                    if not stop_reason:
                        stop_reason = "interrupted by user (Ctrl+C); in-flight requests collected, completed batches saved"
                        print(f"\n[{run_id}] Ctrl+C received - finishing {len(in_flight)} in-flight request(s), "
                              f"then stopping. Press Ctrl+C again to abort immediately.")
                        continue
                    raise
                for fut in done:
                    batch_no, attempt, batch, inv, items, reserve, started = in_flight.pop(fut)
                    resp, error, secs = fut.result()
                    short_to_rep = {sid: rep for (sid, _), (_, rep, _) in zip(items, batch)}
                    valid = validate(resp, items) if resp is not None else {}
                    review_ids = [rep for _, rep, _ in batch]
                    with con:
                        cost = log_call(con, run_id, phase, batch_no, attempt, review_ids, resp, error, len(valid), secs, started)
                    ledger.settle(reserve, cost)
                    finish_batch(batch_no, attempt, batch, {short_to_rep[s]: v for s, v in valid.items()})
                    missing = [b for b in batch if b[1] not in {short_to_rep[s] for s in valid}]
                    status = "ok" if not missing else f"{len(missing)} missing"
                    print(f"  batch {batch_no} attempt {attempt}: {len(valid)}/{len(batch)} valid, {status}, "
                          f"{secs:.1f}s, ${cost:.5f} (spent ${ledger.spent:.4f})")
                    if not missing:
                        continue
                    if error is not None:
                        # API-level failure: bounded backoff retry of the whole request, unless fatal.
                        if is_fatal(error):
                            stop_reason = f"fatal API error: {type(error).__name__}: {str(error)[:200]}"
                        elif attempt < C.MAX_API_ATTEMPTS:
                            time.sleep(min(30, 2 ** attempt) + random.uniform(0, 1))
                            todo.insert(0, (batch_no, attempt + 1, missing, inv))
                        else:
                            print(f"  batch {batch_no}: giving up after {attempt} API attempts; left pending")
                    elif inv < C.MAX_INVALID_OUTPUT_RETRIES:
                        if not valid and len(missing) > 1:
                            # Whole batch unusable (e.g. a looping, truncated response): retry each review on its
                            # own so one problematic text cannot sink the others. Still one retry per review.
                            for item in reversed(missing):
                                todo.insert(0, (batch_no, attempt + 1, [item], inv + 1))
                        else:
                            todo.insert(0, (batch_no, attempt + 1, missing, inv + 1))  # retry only the missing items once
                    else:
                        quarantine(missing, "invalid_model_output_after_retry", attempt)
    except KeyboardInterrupt:
        stop_reason = "interrupted by user (Ctrl+C); completed batches are saved"
        print(f"\n[{run_id}] {stop_reason}")

    counts = {r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) n FROM records GROUP BY status")}
    calls = con.execute("SELECT COUNT(*) n, SUM(outcome='failed') f, SUM(cost_usd) c, SUM(input_tokens) i,"
                        " SUM(cached_tokens) ca, SUM(output_tokens) o FROM calls WHERE run_id=?", (run_id,)).fetchone()
    summary.update({
        "finished_at": now(), "wall_clock_s": round(time.time() - t_start, 2), "stop_reason": stop_reason,
        "record_status": counts, "calls": calls["n"], "failed_calls": calls["f"] or 0,
        "cost_usd": round(calls["c"] or 0, 6), "input_tokens": calls["i"] or 0,
        "cached_input_tokens": calls["ca"] or 0, "output_tokens": calls["o"] or 0,
        "quote_fallbacks": con.execute("SELECT COUNT(*) FROM records WHERE quote_fallback=1 AND run_id=?",
                                       (run_id,)).fetchone()[0],
    })
    out = Path("runs") / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "enrich_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[{run_id}] done in {summary['wall_clock_s']}s | status {counts} | calls {summary['calls']} "
          f"(failed {summary['failed_calls']}) | cost ${summary['cost_usd']:.5f}"
          + (f" | STOPPED: {stop_reason}" if stop_reason else ""))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Paid enrichment run (explicit command).")
    ap.add_argument("--input", required=True, help="input CSV path")
    ap.add_argument("--db", required=True, help="state database (result cache + statuses + call log)")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--phase", default="initial", choices=["initial", "resume"])
    ap.add_argument("--budget-usd", type=float, required=True, help="hard spending cap for this run")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=C.ENRICH_BATCH_SIZE)
    ap.add_argument("--limit", type=int, help="only send the first N distinct pending texts (dev testing)")
    ap.add_argument("--requeue-quarantined", action="store_true",
                    help="give model-output quarantines another pass (logged); empty texts are never requeued")
    a = ap.parse_args()
    if not 1 <= a.batch_size <= 50:
        raise SystemExit("batch size must be between 1 and 50")
    run(a.input, a.db, a.run_id, a.phase, a.budget_usd, a.workers, a.batch_size, a.limit, a.requeue_quarantined)
