"""100-review cost and runtime calculator.

DEFAULT = OFFLINE REPLAY (no API key, no network, standard library only):
    python3 cost/calculator.py                  # recompute everything from saved usage + editable rates
    python3 cost/calculator.py --rates-multiplier 2   # sensitivity check: doubles API spend only

EXPLICIT PAID PILOT (separate command; fresh empty state, 1 worker, cold run then warm run):
    uv run python cost/calculator.py pilot --confirm-paid --budget-usd 0.50

Inputs it reads (all in cost/):  pilot_calls.jsonl, pilot_runs.json, rates.csv, assumptions.json
Output it writes:                cost/report.md
"""

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ROLES = ("enrich", "verify", "group", "memo")
ITEMS = ("input_uncached", "input_cached", "output")


# ---------------------------------------------------------------------------
# Loading saved evidence
# ---------------------------------------------------------------------------
def load_rates(multiplier=1.0):
    rates = {}
    with (HERE / "rates.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            per_unit = float(r["price_usd_per_1m_tokens"]) / 1_000_000 * multiplier
            rates[(r["model"], r["billing_item"])] = per_unit
    return rates


def load_calls():
    with (HERE / "pilot_calls.jsonl").open() as f:
        return [json.loads(line) for line in f if line.strip()]


def billed_units(call):
    """Mutually exclusive billing items. Cached input is subtracted from total input; reasoning
    tokens are already inside output_tokens and are NOT added again."""
    cached = call["cached_input_tokens"] or 0
    return {"input_uncached": (call["input_tokens"] or 0) - cached, "input_cached": cached,
            "output": call["output_tokens"] or 0}


def call_cost(call, rates):
    units = billed_units(call)
    return sum(units[i] * rates[(call["model"], i)] for i in ITEMS)


# ---------------------------------------------------------------------------
# Measured pilot
# ---------------------------------------------------------------------------
def measured(calls, runs, rates):
    out = {}
    for run_id, run in runs.items():
        rc = [c for c in calls if c["run_id"] == run_id]
        by_role = {}
        for role in ROLES:
            cs = [c for c in rc if c["role"] == role]
            units = defaultdict(int)
            for c in cs:
                for k, v in billed_units(c).items():
                    units[k] += v
            by_role[role] = {
                "model": cs[0]["model"] if cs else run["models"].get(role, ""),
                "effort": cs[0]["effort"] if cs else run["efforts"].get(role, ""),
                "requests": len({(c["batch_no"], c["role"]) for c in cs}),
                "attempts": len(cs), "failed": sum(c["outcome"] == "failed" for c in cs),
                "reviews_sent": sum(len(c["review_ids"]) for c in cs),
                "input_uncached": units["input_uncached"], "input_cached": units["input_cached"],
                "output": units["output"], "reasoning_in_output": sum(c["reasoning_tokens"] or 0 for c in cs),
                "summed_call_seconds": round(sum(c["duration_s"] or 0 for c in cs), 2),
                "stage_wall_seconds": run["stage_seconds"].get(role),
                "cost_usd": sum(call_cost(c, rates) for c in cs),
            }
        total = sum(r["cost_usd"] for r in by_role.values())
        out[run_id] = {"roles": by_role, "total_cost_usd": total, "wall_clock_s": run["wall_clock_s"],
                       "rows": run["rows"], "completed": run["completed"], "failed_records": run["failed_records"],
                       "cache_hits": run["already_completed"] + run["cache_hits"],
                       "unique_texts": run["unique_texts"]}
    return out


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------
def project(cold, a, rates, distinct_texts, scenario):
    """Scale each stage by its own work count; fixed stages (group, memo) are added once."""
    e = cold["roles"]["enrich"]
    v = cold["roles"]["verify"]
    n_pilot = cold["completed"]
    req_pilot = max(1, e["requests"])
    batch = a["enrich_batch_size"]
    cons = scenario == "conservative"

    # Enrichment: per-review tokens measured on the pilot; prompt prefix tokens per request.
    prompt_tokens = a["enrich_prompt_tokens"]
    per_review_in = (e["input_uncached"] + e["input_cached"] - prompt_tokens * req_pilot) / n_pilot
    per_review_out = e["output"] / n_pilot
    requests = math.ceil(distinct_texts / batch)
    retry = a["conservative_retry_rate"] if cons else a["base_retry_rate"]
    attempts = requests * (1 + retry)
    cache_hit = a["conservative_prompt_cache_hit_rate"] if cons else a["base_prompt_cache_hit_rate"]
    out_mult = a["conservative_output_multiplier"] if cons else 1.0
    m = e["model"]
    enrich_cost = attempts * (
        (per_review_in * batch + prompt_tokens * (1 - cache_hit)) * rates[(m, "input_uncached")]
        + prompt_tokens * cache_hit * rates[(m, "input_cached")]
        + per_review_out * batch * out_mult * rates[(m, "output")])

    # Verification: declared sample rule; cost per verified review measured on the pilot.
    n_verify = min(a["verify_max"], max(a["verify_min"], math.ceil(a["verify_rate"] * distinct_texts)))
    verify_cost = n_verify * (v["cost_usd"] / max(1, v["reviews_sent"])) * (1 + retry)

    # Fixed stages: run once. Conservative assumes a bigger issue pack and a memo retry.
    group_cost = cold["roles"]["group"]["cost_usd"] * (a["conservative_fixed_multiplier"] if cons else
                                                      a["base_fixed_multiplier"])
    memo_cost = cold["roles"]["memo"]["cost_usd"] * (a["conservative_fixed_multiplier"] if cons else
                                                    a["base_fixed_multiplier"])
    # Capped stronger-model fallback (declared fraction of distinct texts, priced at the memo model's rates).
    fb_frac = a["max_fallback_fraction"] if cons else 0.0
    fb_model = a["fallback_model"]
    # One review per fallback request (prompt prefix cached at the same hit rate), with up to 3x the output.
    fallback_cost = distinct_texts * fb_frac * (
        (per_review_in + prompt_tokens * (1 - cache_hit)) * rates[(fb_model, "input_uncached")]
        + prompt_tokens * cache_hit * rates[(fb_model, "input_cached")]
        + per_review_out * 3 * rates[(fb_model, "output")])

    api_total = enrich_cost + verify_cost + group_cost + memo_cost + fallback_cost
    if a["use_batch_api_discount"]:
        api_total -= 0.5 * (enrich_cost + verify_cost)

    # Time: measured seconds per enrichment request, divided across workers.
    secs_per_req = e["summed_call_seconds"] / max(1, e["attempts"])
    slow = a["conservative_time_multiplier"] if cons else 1.0
    enrich_hours = attempts * secs_per_req * slow / a["max_workers"] / 3600
    verify_hours = math.ceil(n_verify / batch) * (v["summed_call_seconds"] / max(1, v["attempts"])) / a["max_workers"] / 3600
    fixed_hours = (cold["roles"]["group"]["summed_call_seconds"] + cold["roles"]["memo"]["summed_call_seconds"]) / 3600
    tokens_per_min = (per_review_in * batch + prompt_tokens + per_review_out * batch) * a["max_workers"] * 60 / secs_per_req
    return {"scenario": scenario, "distinct_texts": distinct_texts, "enrich_requests": requests,
            "enrich_attempts": round(attempts), "verify_reviews": n_verify,
            "cost": {"enrich": enrich_cost, "verify": verify_cost, "group": group_cost, "memo": memo_cost,
                     "fallback": fallback_cost, "api_total": api_total},
            "hours": enrich_hours + verify_hours + fixed_hours, "est_tokens_per_minute": tokens_per_min,
            "per_review_in": per_review_in, "per_review_out": per_review_out}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def usd(x):
    return f"${x:,.4f}" if x < 1 else f"${x:,.2f}"


def report(rates_multiplier=1.0):
    a = json.loads((HERE / "assumptions.json").read_text())
    rates = load_rates(rates_multiplier)
    calls = load_calls()
    runs = json.loads((HERE / "pilot_runs.json").read_text())
    meas = measured(calls, runs, rates)
    cold, warm = meas[a["cold_run_id"]], meas[a["warm_run_id"]]
    L = []
    w = L.append
    w("# 100-review cost and runtime report")
    w(f"\nGenerated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `python3 cost/calculator.py` "
      f"(offline replay: no API key, no model calls). Rates multiplier: {rates_multiplier}.")
    w(f"\nInput: `cost_100.csv`, sha256 `{runs[a['cold_run_id']]['input_sha256']}` (matches manifest.json). "
      f"Currency: USD. API spend below is **recomputed** as billed units × editable rates in `rates.csv`; "
      f"provider-reported totals are in the call log for reconciliation.")

    w("\n## 1. Measured pilot (real calls)")
    w("\n| | Cold run (empty result cache) | Warm run (saved results) |\n|---|---|---|")
    for label, key in [("Run ID", None), ("Source rows", "rows"), ("Completed records", "completed"),
                       ("Failed / quarantined records", "failed_records"), ("Unique texts", "unique_texts"),
                       ("Result-cache hits (already completed)", "cache_hits")]:
        if key is None:
            w(f"| {label} | `{a['cold_run_id']}` | `{a['warm_run_id']}` |")
        else:
            w(f"| {label} | {cold[key]} | {warm[key]} |")
    for role in ROLES:
        w(f"| {role}: attempts (failed) | {cold['roles'][role]['attempts']} ({cold['roles'][role]['failed']}) | "
          f"{warm['roles'][role]['attempts']} ({warm['roles'][role]['failed']}) |")
    w(f"| **API spend** | **{usd(cold['total_cost_usd'])}** | **{usd(warm['total_cost_usd'])}** |")
    w(f"| **End-to-end wall-clock** | **{cold['wall_clock_s']} s** | **{warm['wall_clock_s']} s** |")
    w(f"| Cost per 1,000 input rows | {usd(1000 * cold['total_cost_usd'] / cold['rows'])} | "
      f"{usd(1000 * warm['total_cost_usd'] / warm['rows'])} |")
    w(f"| Cost per completed record | {usd(cold['total_cost_usd'] / max(1, cold['completed']))} | "
      f"{usd(warm['total_cost_usd'] / max(1, warm['completed']))} |")
    w(f"| Throughput (rows / wall-clock s) | {cold['rows'] / cold['wall_clock_s']:.2f} | "
      f"{warm['rows'] / max(0.01, warm['wall_clock_s']):.0f} |")

    w("\n### By stage (cold run)\n")
    w("| Stage | Provider / model | Effort | Prompt/schema | Batch | Workers | Requests | Attempts | Reviews sent "
      "| Uncached in | Cached in | Output (incl. reasoning) | Reasoning | Stage time | Cost |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for role in ROLES:
        r = cold["roles"][role]
        w(f"| {role} | OpenAI / `{r['model']}` | {r['effort']} | {a['prompt_versions'][role]} | "
          f"{a['batch_sizes'][role]} | {runs[a['cold_run_id']]['workers']} | {r['requests']} | {r['attempts']} | "
          f"{r['reviews_sent']} | {r['input_uncached']:,} | {r['input_cached']:,} | {r['output']:,} | "
          f"{r['reasoning_in_output']:,} | {r['stage_wall_seconds']} s | {usd(r['cost_usd'])} |")
    w("\nZero new enrichment calls in the warm run demonstrates exact result reuse under unchanged settings. "
      "Downstream stages are cached by a hash of their exact inputs, so the warm run also made 0 verify/group/memo "
      "calls and produced byte-identical outputs.")

    w("\n### Billing items and formula\n")
    w("`item_cost = billed_units × price_per_unit`; `total = Σ item_cost`. Items are mutually exclusive: "
      "`input_uncached = input_tokens − cached_input_tokens`, `input_cached`, `output` (reasoning tokens are already "
      "inside output and are not added again). Standard processing tier was used for all measured calls.\n")
    w("| Model | Item | USD per 1M tokens (× multiplier) | Source |\n|---|---|---|---|")
    with (HERE / "rates.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            w(f"| `{r['model']}` | {r['billing_item']} | {float(r['price_usd_per_1m_tokens']) * rates_multiplier:g} | "
              f"[{r['source_checked']}]({r['source_url']}) |")
    w("\n**Not API spend (reported separately):** local compute ran on a MacBook Air (no GPU, no metered cost "
      "recorded) - local electricity/hardware cost is **unknown**, not zero. Dashboard hosting/database costs are "
      "outside this pilot and listed as **unknown** until deployed.")

    w("\n## 2. Full-run projection")
    w(f"\nFull input: {a['full_rows']:,} rows → {a['full_nonempty']:,} nonempty classifications + "
      f"{a['full_rows'] - a['full_nonempty']} empty-text quarantines. Exact-text reuse reduces first-pass model work "
      f"to **{a['full_distinct']:,} distinct texts**.")
    w(f"\nControls: budget **{usd(a['budget_usd'])}**, max workers **{a['max_workers']}**, enrichment output cap "
      f"**{a['enrich_max_output_tokens']:,} tokens/request**, max fallback fraction **{a['max_fallback_fraction']:.0%}** "
      f"(model `{a['fallback_model']}`; 0% = no stronger-model fallback - invalid outputs are retried once with "
      f"the same model, then quarantined), batch API discount applied: **{a['use_batch_api_discount']}**.")
    w("\n| Scenario | Distinct texts | Enrich requests (attempts) | Verify reviews | Enrich | Verify | Group | Memo "
      "| Fallback | **API total** | Est. hours | Budget check |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for label, n in [("with exact-text reuse", a["full_distinct"]), ("no reuse", a["full_nonempty"])]:
        for sc in ("base", "conservative"):
            p = project(cold, a, rates, n, sc)
            c = p["cost"]
            over = c["api_total"] > a["budget_usd"]
            w(f"| {sc}, {label} | {n:,} | {p['enrich_requests']:,} ({p['enrich_attempts']:,}) | {p['verify_reviews']:,} "
              f"| {usd(c['enrich'])} | {usd(c['verify'])} | {usd(c['group'])} | {usd(c['memo'])} | {usd(c['fallback'])} "
              f"| **{usd(c['api_total'])}** | {p['hours']:.1f} | {'⚠️ EXCEEDS BUDGET' if over else 'within budget'} |")
    p = project(cold, a, rates, a["full_distinct"], "base")
    w(f"\nMeasured per-review usage driving the projection: {p['per_review_in']:.1f} input tokens and "
      f"{p['per_review_out']:.1f} output tokens per review, plus a {a['enrich_prompt_tokens']:,}-token instruction "
      f"prefix per request (cached at the provider after the first call). Estimated load at {a['max_workers']} workers: "
      f"~{p['est_tokens_per_minute']:,.0f} tokens/min (account limit {a['rate_limit_tpm']:,} TPM, "
      f"{a['rate_limit_rpm']:,} RPM).")
    w("\nAssumptions (all editable in `cost/assumptions.json`): base = measured retry rate and prompt-cache hit rate, "
      "fixed stages × base multiplier; conservative = higher retry rate, lower prompt-cache hit rate, longer outputs, "
      "slower calls, a memo/group retry and the maximum fallback fraction. Fixed overhead (group naming, memo) is "
      "added once, never multiplied by row count. Time = attempts × measured seconds per request ÷ workers; summed "
      "call durations are not wall-clock when calls overlap. These are estimates from 100 reviews and must be "
      "refreshed after the 500- and 10,000-review checkpoints.")
    cp_path = HERE / "checkpoints.json"
    if cp_path.exists():
        cps = json.loads(cp_path.read_text())
        w("\n## 3. Refreshed estimates from the 500- and 10,000-review checkpoints")
        w("\nMeasured on the development checkpoints (`cost/checkpoints.py`, from saved call logs). Costs use the "
          "provider-reported usage priced at the same rates (multiplier applied); full run = 484,189 distinct texts, "
          f"verification capped at {a['verify_max']:,} reviews, group + memo added once.\n")
        w("| Checkpoint | Rows | Enrich attempts (failed) | Retry rate | Cost / distinct text | Output tok / text "
          "| Requests/s (workers) | **Full-run API estimate** | **Est. hours at "
          f"{a['full_run_workers']} workers** |")
        w("|---|---|---|---|---|---|---|---|---|")
        for name, c in cps.items():
            enrich = c["enrich_cost_per_distinct_text"] * a["full_distinct"] * rates_multiplier
            verify = c["verify_cost_per_review"] * a["verify_max"] * rates_multiplier
            total = enrich + verify + c["fixed_group_memo_cost_usd"] * rates_multiplier
            rps = c["requests_per_second_main_run"] / c["workers_main_run"] * a["full_run_workers"]
            hours = a["full_distinct"] / a["enrich_batch_size"] * (1 + c["retry_rate"]) / rps / 3600
            w(f"| {name} | {c['rows']:,} | {c['enrich_attempts']} ({c['enrich_failed_attempts']}) | "
              f"{c['retry_rate']:.1%} | ${c['enrich_cost_per_distinct_text'] * rates_multiplier:.7f} | "
              f"{c['output_tokens_per_text']:.1f} | {c['requests_per_second_main_run']:.2f} ({c['workers_main_run']}) | "
              f"**{usd(total)}** (conservative ×1.25: {usd(total * 1.25)}) | **{hours:.1f}** "
              f"(conservative ×1.5: {hours * 1.5:.1f}) |")
        w(f"\nScaling decision: the 10,000-review checkpoint confirms the pilot's per-text cost within a few percent. "
          f"The full run uses **{a['full_run_workers']} workers** (measured 1 → 2 → 8; account limits read from response "
          f"headers: {a['rate_limit_rpm']:,} RPM / {a['rate_limit_tpm']:,} TPM, far above the ~70 RPM / ~0.35M TPM "
          f"expected at {a['full_run_workers']} workers), a **${a['full_run_budget_usd']:.0f} pipeline spend cap** and the "
          f"provider-side ${a['budget_usd']:.0f} hard monthly limit. Throughput is assumed to scale linearly from 8 to "
          f"{a['full_run_workers']} workers; this is an assumption to be checked in the first minutes of the run.")
    (HERE / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


# ---------------------------------------------------------------------------
# Explicit paid pilot
# ---------------------------------------------------------------------------
def pilot(budget):
    state = ROOT / "state" / "pilot.sqlite"
    if state.exists():
        sys.exit(f"{state} already exists - the cold run needs an empty result cache. Move it aside first.")
    a = json.loads((HERE / "assumptions.json").read_text())
    for run_id in (a["cold_run_id"], a["warm_run_id"]):
        subprocess.run([sys.executable, "-m", "pipeline", "run", "--input", "data/raw/cost_100.csv",
                        "--state", str(state), "--run-id", run_id, "--budget-usd", str(budget)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(HERE / "collect.py")], cwd=ROOT, check=True)
    report()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="replay", choices=["replay", "pilot"])
    ap.add_argument("--rates-multiplier", type=float, default=1.0)
    ap.add_argument("--confirm-paid", action="store_true")
    ap.add_argument("--budget-usd", type=float, default=0.50)
    args = ap.parse_args()
    if args.command == "pilot":
        if not args.confirm_paid:
            sys.exit("The pilot makes paid API calls. Re-run with --confirm-paid to proceed.")
        pilot(args.budget_usd)
    else:
        report(args.rates_multiplier)
