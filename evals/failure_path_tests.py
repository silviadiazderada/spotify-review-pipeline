"""Failure-path tests with a SIMULATED provider (free, no API key, no network).

Each scenario feeds the real enrichment orchestrator a scripted provider response and checks what the
code does: malformed JSON, missing/unknown ids, a non-substring quote, an empty review, a temporary
rate-limit error, a fatal error, and a spending cap too small for one request.

    uv run python -m evals.failure_path_tests
"""

import csv
import json
import sqlite3
import types
from pathlib import Path

import openai

from pipeline import config as C
from pipeline import enrich

OUT = Path("evals/failure_paths")
TMP = OUT / "tmp"


class RateLimit(Exception):
    status_code = 429


class AuthError(Exception):
    status_code = 401


def labels(item, **over):
    base = {"id": item["id"], "intent": "complaint", "topic": "playback", "severity": 3, "sentiment": -0.5,
            "evidence_quote": item["text"][:15], "entities": [], "needs_review": False}
    base.update(over)
    return base


def response(results=None, raw=None):
    usage = types.SimpleNamespace(input_tokens=500, output_tokens=200, input_tokens_details=None,
                                  output_tokens_details=None)
    text = raw if raw is not None else json.dumps({"results": results})
    return types.SimpleNamespace(id=f"sim_{id(text)}", status="completed", output_text=text, usage=usage)


def scenario(name, rows, script, budget=1.0):
    """script: list of functions(items) -> response or raises; consumed one per call."""
    TMP.mkdir(parents=True, exist_ok=True)
    src, db = TMP / f"{name}.csv", TMP / f"{name}.sqlite"
    for p in (db, Path(f"{db}-wal"), Path(f"{db}-shm")):
        p.unlink(missing_ok=True)
    with src.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["review_id", "review_text", "review_rating", "review_likes", "app_version", "review_timestamp"])
        for rid, text in rows:
            w.writerow([rid, text, "1", "0", "", "2023-01-01 00:00:00"])
    calls = iter(script)

    def create(**kw):
        return next(calls)(json.loads(kw["input"]))

    openai.OpenAI = lambda **kw: types.SimpleNamespace(responses=types.SimpleNamespace(create=create))
    enrich.time.sleep = lambda s: None
    summary = enrich.run(src, db, f"sim-{name}", "initial", budget, 1, 50)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    recs = {r["review_id"]: dict(r) for r in con.execute("SELECT * FROM records")}
    log = [dict(r) for r in con.execute("SELECT attempt, outcome, error, n_valid FROM calls ORDER BY call_id")]
    return summary, recs, log


ROWS = [("SIM-1", "The app crashes when I open it"), ("SIM-2", "Too many ads after every song"),
        ("SIM-3", "Cannot log in at all")]


def main():
    results = []

    def record(name, expectation, ok, summary, recs, log):
        results.append({"scenario": name, "expectation": expectation, "passed": ok,
                        "record_status": {k: (v["status"], v["reason"], v["attempts"]) for k, v in recs.items()},
                        "call_log": log, "stop_reason": summary["stop_reason"]})
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {expectation}")

    # 1. Malformed JSON for the whole batch, then valid retries (one review per retry request).
    s, r, log = scenario("malformed_then_valid", ROWS, [
        lambda items: response(raw='{"results": [ {"id": "r1", "intent": "compl')]
        + [lambda items: response([labels(i) for i in items])] * 3)
    record("malformed_then_valid", "an unusable batch is retried once, one review per request, and completes",
           all(v["status"] == "completed" for v in r.values())
           and [c["outcome"] for c in log] == ["failed", "succeeded", "succeeded", "succeeded"], s, r, log)

    # 2. Malformed on the retry too -> quarantine with reason and attempt count (no silent drop).
    s, r, log = scenario("malformed_twice", ROWS, [lambda items: response(raw="not json")] * 4)
    record("malformed_twice", "after one retry, records are quarantined with a reason and attempts=2",
           all(v["status"] == "quarantined" and v["reason"] == "invalid_model_output_after_retry" and v["attempts"] == 2
               for v in r.values()), s, r, log)

    # 2b. One problematic review makes the whole batch fail (as seen in dev-10k batch 88): isolated on retry.
    def only_sim2_breaks(items):
        if any("ads" in i["text"] for i in items):
            return response(raw='{"results": [{"id": "r1", "entities": ["x", "x", "x", "x"')  # truncated / looping
        return response([labels(i) for i in items])
    s, r, log = scenario("one_bad_review_isolated", ROWS, [only_sim2_breaks] * 4)
    record("one_bad_review_isolated", "a batch sunk by one review is retried per review: only that review is quarantined",
           r["SIM-1"]["status"] == "completed" and r["SIM-3"]["status"] == "completed"
           and r["SIM-2"]["status"] == "quarantined", s, r, log)

    # 3. Missing id + unknown id -> only the missing item is retried; unknown id rejected.
    s, r, log = scenario("missing_and_unknown_ids", ROWS, [
        lambda items: response([labels(items[0]), labels(items[1]), labels({"id": "r99", "text": "x"})]),
        lambda items: response([labels(i) for i in items])])
    record("missing_and_unknown_ids", "unknown id r99 is ignored; only the missing review is re-sent",
           all(v["status"] == "completed" for v in r.values()) and log[1]["n_valid"] == 1, s, r, log)

    # 4. Quote that is not an exact substring -> replaced in code by the full text, flagged.
    s, r, log = scenario("bad_quote", ROWS[:1], [lambda items: response([labels(items[0], evidence_quote="crashes on start")])])
    record("bad_quote", "a non-substring quote is replaced by the exact full text and flagged quote_fallback",
           r["SIM-1"]["evidence_quote"] == ROWS[0][1] and r["SIM-1"]["quote_fallback"] == 1, s, r, log)

    # 5. Empty review text -> quarantined without any model call.
    s, r, log = scenario("empty_text", [("SIM-E", "   "), ROWS[0]], [lambda items: response([labels(i) for i in items])])
    record("empty_text", "whitespace-only text is quarantined as empty_review_text and never sent",
           r["SIM-E"]["status"] == "quarantined" and r["SIM-E"]["reason"] == "empty_review_text"
           and len(log) == 1, s, r, log)

    # 6. Temporary rate limit, then success (bounded backoff).
    def rate_limited(items):
        raise RateLimit("429 rate limited (simulated)")
    s, r, log = scenario("rate_limit_then_ok", ROWS, [rate_limited, lambda items: response([labels(i) for i in items])])
    record("rate_limit_then_ok", "a 429 is logged as a failed attempt, retried with backoff, then completes",
           all(v["status"] == "completed" for v in r.values()) and [c["outcome"] for c in log] == ["failed", "succeeded"],
           s, r, log)

    # 7. Fatal error (bad key) -> stop immediately, records stay pending (resumable), no retries.
    def auth_fail(items):
        raise AuthError("401 invalid api key (simulated)")
    s, r, log = scenario("fatal_auth_error", ROWS, [auth_fail])
    record("fatal_auth_error", "a 401 stops the run after one attempt; records stay pending for a later resume",
           all(v["status"] == "pending" for v in r.values()) and len(log) == 1 and "fatal" in (s["stop_reason"] or ""),
           s, r, log)

    # 7b. Provider credit exhausted (429 insufficient_quota, seen in the full run): stop at once, keep pending.
    class NoCredits(Exception):
        status_code = 429
    def no_credits(items):
        raise NoCredits("Error code: 429 - {'error': {'message': 'You have no credits remaining.', "
                        "'type': 'insufficient_quota', 'code': 'insufficient_quota'}}")
    s, r, log = scenario("credits_exhausted", ROWS, [no_credits])
    record("credits_exhausted", "a 429 insufficient_quota stops the run after one attempt; records stay pending",
           all(v["status"] == "pending" for v in r.values()) and len(log) == 1 and "fatal" in (s["stop_reason"] or ""),
           s, r, log)

    # 8. Spending cap smaller than one request's worst case -> no call is made.
    s, r, log = scenario("budget_cap", ROWS, [], budget=0.0001)
    record("budget_cap", "the spend ledger refuses to dispatch when the worst-case cost exceeds the cap",
           len(log) == 0 and (s["stop_reason"] or "").startswith("budget"), s, r, log)

    out = {"simulated_provider": True, "no_api_calls": True, "enrich_label_config": C.ENRICH_LABEL_CONFIG,
           "passed": sum(x["passed"] for x in results), "total": len(results), "scenarios": results}
    (OUT / "failure_path_results.json").write_text(json.dumps(out, indent=2))
    print(f"{out['passed']}/{out['total']} failure-path scenarios passed")


if __name__ == "__main__":
    main()
