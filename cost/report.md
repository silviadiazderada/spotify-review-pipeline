# 100-review cost and runtime report

Generated 2026-10-08 02:43 UTC by `python3 cost/calculator.py` (offline replay: no API key, no model calls). Rates multiplier: 1.0.

Input: `cost_100.csv`, sha256 `c884ac3b9be5066995d5063f96ad9af6e5e082975788c1684c4f6b6ea661dd0e` (matches manifest.json). Currency: USD. API spend below is **recomputed** as billed units × editable rates in `rates.csv`; provider-reported totals are in the call log for reconciliation.

## 1. Measured pilot (real calls)

| | Cold run (empty result cache) | Warm run (saved results) |
|---|---|---|
| Run ID | `pilot-cold` | `pilot-warm` |
| Source rows | 100 | 100 |
| Completed records | 100 | 100 |
| Failed / quarantined records | 0 | 0 |
| Unique texts | 100 | 100 |
| Result-cache hits (already completed) | 0 | 100 |
| enrich: attempts (failed) | 2 (0) | 0 (0) |
| verify: attempts (failed) | 1 (0) | 0 (0) |
| group: attempts (failed) | 1 (0) | 0 (0) |
| memo: attempts (failed) | 1 (0) | 0 (0) |
| **API spend** | **$0.0178** | **$0.0000** |
| **End-to-end wall-clock** | **64.72 s** | **0.51 s** |
| Cost per 1,000 input rows | $0.1782 | $0.0000 |
| Cost per completed record | $0.0002 | $0.0000 |
| Throughput (rows / wall-clock s) | 1.55 | 196 |

### By stage (cold run)

| Stage | Provider / model | Effort | Prompt/schema | Batch | Workers | Requests | Attempts | Reviews sent | Uncached in | Cached in | Output (incl. reasoning) | Reasoning | Stage time | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| enrich | OpenAI / `gpt-6-luna` | none | enrich-v1 / schema-v1 | 50 | 1 | 2 | 2 | 100 | 4,730 | 1,517 | 4,481 | 0 | 34.83 s | $0.0027 |
| verify | OpenAI / `gpt-6-luna` | low | verify-v1 | 50 | 1 | 1 | 1 | 20 | 1,254 | 0 | 772 | 393 | 7.85 s | $0.0005 |
| group | OpenAI / `gpt-6-luna` | low | group-v1 / issues-v1 | all issues (1 request) | 1 | 1 | 1 | 0 | 1,227 | 0 | 605 | 0 | 6.97 s | $0.0004 |
| memo | OpenAI / `gpt-6.1-sol` | low | memo-v1 | 1 evidence pack | 1 | 1 | 1 | 0 | 3,005 | 0 | 814 | 0 | 15.06 s | $0.0142 |

Zero new enrichment calls in the warm run demonstrates exact result reuse under unchanged settings. Downstream stages are cached by a hash of their exact inputs, so the warm run also made 0 verify/group/memo calls and produced byte-identical outputs.

### Billing items and formula

`item_cost = billed_units × price_per_unit`; `total = Σ item_cost`. Items are mutually exclusive: `input_uncached = input_tokens − cached_input_tokens`, `input_cached`, `output` (reasoning tokens are already inside output and are not added again). Standard processing tier was used for all measured calls.

| Model | Item | USD per 1M tokens (× multiplier) | Source |
|---|---|---|---|
| `gpt-6-luna` | input_uncached | 0.1 | [2026-10-06](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| `gpt-6-luna` | input_cached | 0.01 | [2026-10-06](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| `gpt-6-luna` | output | 0.5 | [2026-10-06](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| `gpt-6.1-sol` | input_uncached | 2 | [2026-10-07](https://developers.openai.com/api/docs/models/gpt-6.1-sol) |
| `gpt-6.1-sol` | input_cached | 0.1 | [2026-10-07](https://developers.openai.com/api/docs/models/gpt-6.1-sol) |
| `gpt-6.1-sol` | output | 10 | [2026-10-07](https://developers.openai.com/api/docs/models/gpt-6.1-sol) |

**Not API spend (reported separately):** local compute ran on a MacBook Air (no GPU, no metered cost recorded) - local electricity/hardware cost is **unknown**, not zero. Dashboard hosting/database costs are outside this pilot and listed as **unknown** until deployed.

## 2. Full-run projection

Full input: 660,622 rows → 660,609 nonempty classifications + 13 empty-text quarantines. Exact-text reuse reduces first-pass model work to **484,189 distinct texts**.

Controls: budget **$50.00**, max workers **10**, enrichment output cap **8,000 tokens/request**, max fallback fraction **0%** (model `gpt-6.1-sol`; 0% = no stronger-model fallback - invalid outputs are retried once with the same model, then quarantined), batch API discount applied: **False**.

| Scenario | Distinct texts | Enrich requests (attempts) | Verify reviews | Enrich | Verify | Group | Memo | Fallback | **API total** | Est. hours | Budget check |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base, with exact-text reuse | 484,189 | 9,684 (9,684) | 2,000 | $12.62 | $0.0511 | $0.0004 | $0.0142 | $0.0000 | **$12.68** | 4.7 | within budget |
| conservative, with exact-text reuse | 484,189 | 9,684 (10,652) | 2,000 | $17.52 | $0.0563 | $0.0013 | $0.0425 | $0.0000 | **$17.62** | 7.7 | within budget |
| base, no reuse | 660,609 | 13,213 (13,213) | 2,000 | $17.22 | $0.0511 | $0.0004 | $0.0142 | $0.0000 | **$17.28** | 6.4 | within budget |
| conservative, no reuse | 660,609 | 13,213 (14,534) | 2,000 | $23.90 | $0.0563 | $0.0013 | $0.0425 | $0.0000 | **$24.00** | 10.5 | within budget |

Measured per-review usage driving the projection: 32.1 input tokens and 44.8 output tokens per review, plus a 1,517-token instruction prefix per request (cached at the provider after the first call). Estimated load at 10 workers: ~186,412 tokens/min (account limit 2,000,000 TPM, 5,000 RPM).

Assumptions (all editable in `cost/assumptions.json`): base = measured retry rate and prompt-cache hit rate, fixed stages × base multiplier; conservative = higher retry rate, lower prompt-cache hit rate, longer outputs, slower calls, a memo/group retry and the maximum fallback fraction. Fixed overhead (group naming, memo) is added once, never multiplied by row count. Time = attempts × measured seconds per request ÷ workers; summed call durations are not wall-clock when calls overlap. These are estimates from 100 reviews and must be refreshed after the 500- and 10,000-review checkpoints.

## 3. Refreshed estimates from the 500- and 10,000-review checkpoints

Measured on the development checkpoints (`cost/checkpoints.py`, from saved call logs). Costs use the provider-reported usage priced at the same rates (multiplier applied); full run = 484,189 distinct texts, verification capped at 2,000 reviews, group + memo added once.

| Checkpoint | Rows | Enrich attempts (failed) | Retry rate | Cost / distinct text | Output tok / text | Requests/s (workers) | **Full-run API estimate** | **Est. hours at 16 workers** |
|---|---|---|---|---|---|---|---|---|
| checkpoint_500 | 500 | 10 (0) | 0.0% | $0.0000261 | 45.3 | 0.08 (1) | **$12.70** (conservative ×1.25: $15.87) | **2.1** (conservative ×1.5: 3.2) |
| analysis_10000 | 10,000 | 171 (2) | 1.2% | $0.0000271 | 47.4 | 0.56 (8) | **$13.16** (conservative ×1.25: $16.45) | **2.4** (conservative ×1.5: 3.7) |

Scaling decision: the 10,000-review checkpoint confirms the pilot's per-text cost within a few percent. The full run uses **16 workers** (measured 1 → 2 → 8; account limits read from response headers: 5,000 RPM / 2,000,000 TPM, far above the ~70 RPM / ~0.35M TPM expected at 16 workers), a **$30 pipeline spend cap** and the provider-side $50 hard monthly limit. Throughput is assumed to scale linearly from 8 to 16 workers; this is an assumption to be checked in the first minutes of the run.
