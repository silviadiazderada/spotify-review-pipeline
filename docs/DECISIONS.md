# Design decisions log

Running record of choices and why. Feeds the README's "design choices" section.

## D1 — Prepare and deduplicate with code before any model call (2026-10-06)

- Stage 1 (`scripts/01_prepare.py`) reads all 660,622 rows with a plain CSV parser and makes no model calls.
- Results match the brief: 0 duplicate IDs, 13 empty texts quarantined, 159,701 missing app versions, 660,609 nonempty texts.
- Exact-text reuse brings this down to **484,189 distinct texts**, so 176,420 rows (27%) reuse a result instead of triggering a new model call. Every original ID is kept, and `cache_source_id` records which review's result was reused.
- The most repeated texts are short generic praise: "Good" ×12,845, "Nice" ×5,551, "Excellent" ×4,096.
- Median distinct text is 55 characters. All distinct texts together come to about 12M tokens, so input volume is small.
- Runtime is about 5 s and the cost is $0.

## D2 — Provider choice: OpenAI GPT-6 Luna for bulk enrichment (2026-10-06)

The grading is provider-neutral. Classifying about 484k short reviews into fixed labels is a bounded, high-volume task, so price per token dominates.

| Model | Input / output per 1M tokens | Brief's illustrative full-run estimate |
|---|---|---|
| OpenAI GPT-6 Luna | $0.10 / $0.50 (rate from the course brief) | about $41 after exact-text reuse |
| Claude Haiku 4.5 | $1.00 / $5.00 (Anthropic published rate) | about $410, or about $205 with the 50%-off Batch API |
| Claude Sonnet 5 | $2.00 / $10.00 | about $1,123 before reuse (brief) |

- Luna is about 10× cheaper than the cheapest Claude model for this workload.
- We use the lowest reasoning effort that passes the golden-set evaluation.
- Jev (TypeSafe) is skipped for now to keep a single provider and a single key. This can be revisited if Luna's label quality is weak.
- A stronger model is reserved for a capped fallback share of hard cases, if the measured benefit justifies it.
- **To do:** verify these rates against the live price pages on the day of the pilot, and record the date in `cost/rates.csv`.

## D3 — Two independent spending controls (2026-10-06)

1. **Provider side:** OpenAI project monthly hard limit of $50. When it is reached, requests fail with HTTP 429.
2. **Pipeline side (to build):** a spend ledger in our own code. It reserves the estimated cost before each request and stops admitting work when spent + reserved would exceed the cap.

A 429 is treated as stop, save, and resume, never as a completed record.

## D4: Golden 50 labeled by a human before any model run (2026-10-06)

- **Who labeled:** Silvia hand-labeled all 50 rows of `golden_50_to_label.csv` in `evals/golden_50_labeling.xlsx`. The sheet has dropdowns for the shared labels and a guide tab.
- **Pre-evaluation consistency check:** a script compared the labels against the shared rules and flagged combinations they forbid. Examples: complaint with severity 1, request/unclear with severity above 1. This flagged 9 rows. Silvia re-read each one and corrected them herself. The script never proposed specific labels.
- **No model involvement:** no model predictions existed at that point, so the golden labels were not tuned toward model output.
- **Frozen file:** labels are frozen in `evals/golden_50_human.csv` (sha256 `2d677c4fc1199652083136f83b96bdcda7764dd5f5e2a1ae5c23d53b7811d5f7`). Any later change must be disclosed.
- **Kept out of prompts:** golden labels never enter prompts, examples or thresholds. The prompt examples in `docs/LABEL_GUIDE.md` are invented.
- **Distribution:**
  - intent: praise 20, complaint 16, unclear 9, cancellation 3, request 2
  - 10 rows are marked `needs_review`; reasons are to be added during error analysis.

## D5: First real enrichment trial on cost_100 (2026-10-07 04:57 UTC, run `dev-100`)

This was a development run of **enrichment only**. The official graded pilot (all stages, cold then warm) will be rerun once verification, grouping, ranking and memo exist.

**Setup:** `gpt-6-luna`, reasoning effort `none`, prompt `enrich-v1`, schema `schema-v1`, batches of 50 reviews, 1 worker, $0.10 cap. The cost_100 input checksum matches the manifest.

**Measured result:**
- 100/100 records completed in 2 requests.
- 0 failed calls and 0 retries.
- 29.6 s wall-clock (about 15 s per request).
- **$0.0027 total**.

**Usage:**
- Input: 6,247 tokens, of which 1,517 were cached. The second request reused the prompt prefix at $0.01/M.
- Output: 4,471 tokens, about 45 per review.

**Quote validation:** 1 model quote failed exact-substring validation. The model had "corrected" the text, so code replaced it with the full review text.

**Rough full-run projection** (484,189 distinct texts ≈ 9,684 requests at about $0.0013 each). This is to be refreshed at 500 and 10k:

| Scenario | Estimated cost |
|---|---|
| Standard tier | about $12–13 |
| Batch API (50% off) | about $6–7 |

**Time is the constraint, not money.** At about 15 s per request, one worker would take about 40 h. Plan: run concurrent workers within rate limits (Build tier: 5,000 RPM / 2M TPM), or use the Batch API.

**Early signal (n=100, not yet evaluated):** several complaints concern free-tier restrictions (no song choice, skip limits), which the shared rules classify as `billing`.

## D6: Full 6-stage pipeline and official 100-review pilot (2026-10-07)

**Stages and owners.** Code owns IDs, hashing, caching, batching, validation, retries, budgets, membership and arithmetic. Models only interpret language.

| Stage | Done by | Model and settings | Prompt / version |
|---|---|---|---|
| enrich | model | `gpt-6-luna`, effort none | `enrich-v1` |
| verify | independent model task | `gpt-6-luna`, effort low (deliberately a different config) | `verify-v1` |
| group (membership) | code | none: keyword rules `issues-v1` | — |
| group (issue naming) | model | `gpt-6-luna`, effort low | `group-v1` |
| rank | code only | none | — |
| memo | model | `gpt-6.1-sol`, effort low | `memo-v1` |

- **Verify:** re-labels a declared 20% sample (min 20, max 2,000) without seeing the first answer.
- **Group:** membership is code-only, so it can be re-tuned with no model cost. The model only names issues from at most 8 example quotes each.
- **Memo:** one call over a code-built evidence pack. Code checks every claim ID, issue ID, review ID and number. One corrective retry is allowed.
- **Fallback:** none. The declared maximum fallback fraction is 0%. Invalid outputs are retried once with the same model, then quarantined.

**Pilot measurements.** Run on `cost_100.csv` with 1 worker and an empty state.

| Run | Calls | Spend | Wall-clock | Notes |
|---|---|---|---|---|
| `pilot-cold` | 5 (enrich 2, verify 1, group 1, memo 1), 0 failed | **$0.0178**, of which memo $0.0142 | **64.7 s** | Verifier agreement: intent 0.95, topic 0.90, severity 0.95 (n=20). Memo check passed first try. |
| `pilot-warm` | **0 in every stage** | $0 | **0.51 s** | All outputs byte-identical to the cold run. |

**Checks.**
- The offline rerank reproduces `ranking.csv` exactly.
- The course `check_submission.py` accepted the export format on a mock run. Its ranking recomputation matched ours.

**Calculator** (`cost/`, offline by default):
- Doubling rates doubles API spend ($0.0178 → $0.0356), and measured time is unchanged.
- Full-run projection with exact-text reuse: **$12.68 base / $17.62 conservative**, about 4.7–7.7 h at 10 workers.
- Without reuse: $17.28 / $24.00.
- All scenarios are within the $50 budget. To be refreshed at 500 and 10k.

## D7: Golden-50 evaluation of `enrich-v1` (2026-10-07)

**Primary results** (original frozen human labels):

| Field | Result |
|---|---|
| Intent | 84% agreement |
| Topic | 70% agreement |
| Severity | 74% exact agreement, MAE 0.32 |
| Sentiment | 92% within ±0.5 |
| Evidence quotes | 50/50 exact substrings |

**Error analysis** of the 21 disagreements (`evals/golden_eval/error_analysis.md`):
- 2 clear model errors.
- 11 cases where the human label contradicted the written contract.
- 8 genuinely ambiguous cases.

**Disclosed secondary diagnostic.** Silvia reviewed the analysis and accepted the rule-based labels for the B cases. Because this was adjudicated after the predictions were seen, the frozen file was not edited. A disclosed rule-adjusted reference (10 cases) gives: intent 90%, topic 84%, severity 76%.

**No prompt change was made based on the golden set.** The two model-error patterns (severity inflation from alarming words; Premium-restricted controls labeled usability) are checked on the development data next.

## D8: 500-review checkpoint and issue rules v2 (2026-10-07)

**Run `dev-500`** (`checkpoint_500.csv`, 1 worker):
- 500/500 completed; 479 distinct texts in 10 requests.
- 0 failed calls; **$0.0299** in 193 s.
- Verifier (96 sampled texts): intent 97%, topic 85%, severity 91%, severity MAE 0.10.

**Golden error patterns at scale:**
- **Severity-5 inflation is rare.** 4/500 reviews scored 5, and 3 of those are explicit data loss ("deleted everything", "hacked, can't recover playlists"). Only 1 is inflated.
- **Premium-locked controls labeled usability: about 5/500.** Most usability reviews that mention Premium are about ads, and the rules correctly place those under usability.
- **Decision:** keep prompt `enrich-v1`. The gain does not justify a prompt change plus fresh held-out labels before the deadline. Both patterns are documented as limitations.

**Grouping v1 → v2 (code only, tuned on development data, not on the golden set).** Large "general" buckets hid themes, so we added subtopics:

| Topic | New subtopics |
|---|---|
| billing | `basic_features_paywalled`, `plan_purchase_activation` |
| usability | `shuffle_skip_limits`; the ads rule now catches the common misspelling "adds" and "comercial" |
| playback | `wont_play`, `plays_wrong_songs` |

| Bucket | v1 | v2 |
|---|---|---|
| billing-general | 25 | 6 |
| usability-general | 21 | 7 |
| playback-general | 14 | 8 |

- **Run `dev-500-v2`:** 0 enrich/verify calls (cached). Only issue naming and the memo re-ran: $0.0156.
- **Top-ranked issues** at n=500: usability-ads (68), billing-basic_features_paywalled (51), usability-shuffle_skip_limits (44).
- **Theme:** "free-tier restrictions" spans billing and usability. The memo must mention that this boundary affects area totals.

## D9: System tests (2026-10-07)

All tests are synthetic and excluded from business results.

### Planted errors (`evals/planted_error_test.py`)

Run on a separate test copy of the dev-500 state. The verifier never sees enrichment labels.
- **Gross errors** (intent, topic and severity all flipped): **10/10 detected**.
- **Subtle errors** (topic moved to a neighbouring category only): **8/10 detected**.
  - Both misses are billing→usability on free-tier restriction reviews ("only 6 skips a day, can't pick the song"). The verifier itself reads these as usability.
  - This is the same taxonomy boundary found in the golden analysis.
  - Limitation: verification cannot police that boundary.

### Prompt injection (`evals/injection_test.py`)

One real request ($0.0003) with 5 hostile reviews and 4 controls in the same batch.
- **9/9 passed.**
- No hostile review got the label it demanded, and all were marked needs_review.
- Hostile reviews that also described a real problem were labeled by that problem.
- All 4 controls were labeled correctly, and all ids came back.

### Failure paths (`evals/failure_path_tests.py`)

Simulated provider, free. **8/8 scenarios passed**:
1. Malformed JSON → one retry → success.
2. Malformed twice → quarantined (`invalid_model_output_after_retry`, attempts=2).
3. Unknown id rejected; only the missing item is re-sent.
4. A non-substring quote is replaced by the full text and flagged.
5. Empty text is quarantined without a call.
6. 429 → backoff → success.
7. 401 → immediate stop with records left pending (resumable).
8. A budget cap below one request's worst case → no dispatch.

### Concurrency (dev-10k)

- 1,000 distinct texts (2,188 rows thanks to exact-text reuse) with **2 workers**: 20 requests in 141 s.
- That is about 7 s per request effective, versus about 14 s with 1 worker.
- The rest of the run uses 8 workers (see D10).

## D10: 10,000-review checkpoint, retry isolation, full-run plan (2026-10-07)

**Run `dev-10k`** (`analysis_10000.csv`):
- 1,000 distinct texts with 2 workers, then the rest with 8 workers.
- 8 workers sustained 0.56 requests/s (about 28 reviews/s), with no rate-limit errors.
- Enrich: 171 attempts, 2 failed; $0.229 in total.
- Verify: 1,680 sampled texts. Agreement: intent 95%, topic 90%, severity 91%.

**Failure found and fixed.**
- One batch of 50 returned a degenerate, looping answer that hit the 8,000-token output cap (`status=incomplete`), twice.
- Under the "retry once, then quarantine" rule, all 51 rows were quarantined.
- Fix (enrichment logic only; `label_config` is unchanged because prompt, schema, model and effort are the same):
  1. When a whole batch is unusable, the retry sends **each review on its own**, so one bad text cannot sink 49 others.
  2. The output cap now scales with batch size: `min(8000, 300 + 120 × reviews)`. This limits the cost of a looping response.
- The 51 rows were requeued with the explicit, logged `--requeue-quarantined` flag (run `dev-10k-requeue`). All 50 texts completed on the first attempt, so the loop was intermittent rather than caused by a specific text.
- Simulated test `one_bad_review_isolated` added. Failure-path tests: 9/9 pass.

**Account limits** read from response headers: 5,000 RPM / 2,000,000 TPM.

**Refreshed estimate** (`cost/report.md` §3): $13.16 API cost (conservative $16.45) and about 2.4 h at 16 workers.

**Full-run controls:**
- 16 workers.
- $30 pipeline spend cap, plus the $50 provider hard limit.
- Interruption/resume demonstrated at the start of the run, with a screen recording and checkpoint snapshots.

## D11: Full-corpus run (2026-10-07 21:11 PT → 2026-10-08 08:52 PT)

Input `spotify_reviews_18months.csv` (sha256 `1fc85de6…2fcef6`). State `state/full.sqlite`. 16 workers, $30 pipeline cap.

| Run | Phase | Enrich calls (failed) | Spend | What happened |
|---|---|---|---|---|
| `full-initial` | initial | 10 (0) | $0.013 | Interrupted with Ctrl+C on camera after about 2 min. `grading/checkpoint_before.json` = 58,819 completed IDs (many from the most-repeated texts). |
| `full-resume` | resume | 7,641 (40) | $8.194 | Resumed on camera. `checkpoint_after.json` = 70,288 IDs. 0 resume requests contained a checkpointed ID. Then ran overnight, **slowly** (see failure 1). |
| `full-resume-2` | resume | 1,504 (204) | $1.423 | Fast after the index fix, until the prepaid **OpenAI credit ran out** (see failure 2). |
| `full-resume-3` | resume | 3,238 (18) | $3.602 | After $10 was added: finished all remaining texts in 48 min. |

**Result:** 660,622 rows accounted for.
- **660,600 completed** (99.9986% of the 660,609 nonempty texts).
- 13 quarantined as `empty_review_text`.
- 9 quarantined as `invalid_model_output_after_retry`: degenerate outputs that recurred even on their single-review retry.
- Enrichment spend **$13.23**, including tests.

### Failure 1: query plan at scale

- **Symptom:** the overnight run achieved only about 0.2 requests/s (expected about 1.1).
- **Cause:** SQLite chose the low-cardinality `status` index for `WHERE text_sha256=? AND status='pending'`. That meant scanning about 570k pending rows for every text in every batch. It was invisible at 10k rows.
- **Fix:** composite index `records(text_sha256, status)`, verified with `EXPLAIN QUERY PLAN` on a copy. The run was stopped gracefully with SIGINT and resumed as `full-resume-2` at about 1.3 requests/s.
- **Cost of the interruptions:** each one abandoned up to 16 in-flight requests. Their charges (estimated at most about $0.02 each time) are not in the call log. To reconcile against the provider usage page.

### Failure 2: prepaid credit exhausted

- **Symptom:** OpenAI returned `429 insufficient_quota` ("no credits remaining") at about 07:28 PT. This was the provider-side spending control, not our cap.
- **Bug:** the code treated it like a transient rate limit and retried every batch 3 times. The 204 failed attempts cost nothing, but the run wasted time.
- **Handling:** records stayed `pending`, the run was stopped, credits were added, and the run resumed as `full-resume-3`.
- **Fix:** `insufficient_quota` is now fatal in `is_fatal()`, so the run stops immediately and keeps records pending. Simulated test `credits_exhausted` added; failure-path tests now pass 10/10.

### Screen recording

- The original 6:21 recording (`full-initial` → Ctrl+C → checkpoint → `full-resume` → second-tab checkpoint) was saved by macOS to Photos.
- For publication it was edited to `evidence/resume_demo_redacted.mp4` (3:37, about 1.8 MB):
  - the audio track was removed;
  - the chat-assistant window segments were cut, keeping only the 10 Terminal segments in order, with timestamps detected by frame brightness;
  - the Terminal tab bar (unrelated project names) was pixelated, with the layout detected per quarter-second.
- No Terminal output was altered. The unedited original is kept privately.
