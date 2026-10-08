"""One provider adapter for the downstream roles (verify, group, memo): a bounded call, an
inspectable call-log row, and a per-run spending check. Enrichment has its own orchestrator."""

import hashlib
import json
import time
from datetime import datetime, timezone

from pipeline import config as C


class BudgetStop(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def make_client():
    from dotenv import load_dotenv
    from openai import OpenAI  # imported lazily so offline commands never need the SDK or a key

    load_dotenv()
    return OpenAI(max_retries=0, timeout=180)


def input_hash(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def run_spend(con, run_id):
    return con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM calls WHERE run_id=?", (run_id,)).fetchone()[0]


def reserve(con, run_id, budget, model, instructions, payload, max_output_tokens):
    """Stop before dispatch if spent + worst-case cost of this call would exceed the run budget."""
    worst = C.call_cost(model, int((len(instructions) + len(payload)) / 3), 0, max_output_tokens)
    spent = run_spend(con, run_id)
    if spent + worst > budget:
        raise BudgetStop(f"spent ${spent:.4f} + next call worst case ${worst:.4f} > run cap ${budget:.2f}")


def call(client, *, model, effort, instructions, payload, max_output_tokens, cache_key, schema=None, schema_name=None):
    kwargs = dict(model=model, reasoning={"effort": effort}, instructions=instructions, input=payload,
                  max_output_tokens=max_output_tokens, prompt_cache_key=cache_key, store=False)
    if schema is not None:
        kwargs["text"] = {"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": True}}
    t0 = time.time()
    try:
        return client.responses.create(**kwargs), None, time.time() - t0
    except Exception as e:
        return None, e, time.time() - t0


def log_call(con, *, run_id, role, phase, model, effort, config, batch_no, attempt, review_ids,
             resp, error, ok, n_valid, seconds, started):
    usage = getattr(resp, "usage", None)
    inp = getattr(usage, "input_tokens", 0) or 0
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    reasoning = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", 0) or 0
    cost = C.call_cost(model, inp, cached, out)
    if isinstance(error, Exception):
        error = f"{type(error).__name__}: {error}"[:500]
    with con:
        con.execute(
            "INSERT INTO calls(request_id, run_id, role, phase, model, effort, label_config, batch_no, attempt,"
            " review_ids, outcome, error, n_valid, input_tokens, cached_tokens, output_tokens, reasoning_tokens,"
            " cost_usd, started_at, duration_s) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (getattr(resp, "id", None) or f"local-{run_id}-{role}-{batch_no}-{attempt}", run_id, role, phase, model,
             effort, config, batch_no, attempt, json.dumps(review_ids), "succeeded" if ok else "failed", error,
             n_valid, inp, cached, out, reasoning, cost, started, round(seconds, 3)))
    return cost


def is_fatal(error):
    status = getattr(error, "status_code", None)
    # "No credits" arrives as a 429 like a rate limit, but retrying cannot help: stop and keep records pending.
    quota = "insufficient_quota" in f"{getattr(error, 'code', '')} {error}"
    return status in (400, 401, 403, 404) or quota


def get_artifact(con, key):
    row = con.execute("SELECT output FROM artifacts WHERE key=?", (key,)).fetchone()
    return json.loads(row["output"]) if row else None


def put_artifact(con, key, role, config, output):
    with con:
        con.execute("INSERT OR REPLACE INTO artifacts(key, role, config, output, created_at) VALUES (?,?,?,?,?)",
                    (key, role, config, json.dumps(output, ensure_ascii=False), now()))
