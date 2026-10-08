"""Versioned settings for every model role. Changing any of these changes label_config,
which means saved results are no longer reused (the cache key includes it)."""

from pathlib import Path

PROMPTS = Path(__file__).parent / "prompts"

# --- Enrichment role -------------------------------------------------------
ENRICH_MODEL = "gpt-6-luna"
ENRICH_EFFORT = "none"            # cheapest supported reasoning setting; model default is "medium"
ENRICH_PROMPT_VERSION = "enrich-v1"
ENRICH_SCHEMA_VERSION = "schema-v1"
ENRICH_BATCH_SIZE = 50            # course limit: at most 50 reviews per request
ENRICH_MAX_OUTPUT_TOKENS = 8000   # hard cap per request (~50 reviews x ~70 tokens + margin)
ENRICH_LABEL_CONFIG = f"{ENRICH_MODEL}+effort-{ENRICH_EFFORT}+{ENRICH_PROMPT_VERSION}+{ENRICH_SCHEMA_VERSION}"

# --- Rates (USD per 1M tokens), standard tier --------------------------------
# Source: https://developers.openai.com/api/docs/models/gpt-6-luna (checked 2026-10-06)
RATES = {
    "gpt-6-luna": {"input": 0.10, "cached_input": 0.01, "output": 0.50},
    # Source: https://developers.openai.com/api/docs/models/gpt-6.1-sol (checked 2026-10-07)
    "gpt-6.1-sol": {"input": 2.00, "cached_input": 0.10, "output": 10.00},
}

# --- Verification role (independent re-label of a declared random sample) ---
VERIFY_MODEL = "gpt-6-luna"
VERIFY_EFFORT = "low"             # deliberately a different setting from the enricher
VERIFY_PROMPT_VERSION = "verify-v1"
VERIFY_CONFIG = f"{VERIFY_MODEL}+effort-{VERIFY_EFFORT}+{VERIFY_PROMPT_VERSION}"
VERIFY_RATE, VERIFY_MIN, VERIFY_MAX = 0.20, 20, 2000   # 20% sample of distinct texts, at least 20, at most 2,000
VERIFY_SEED = "a5-verify-v1"
VERIFY_MAX_OUTPUT_TOKENS = 12000  # low effort may add reasoning tokens (billed as output)

# --- Grouping role (code assigns membership; the model only names issues) ---
GROUP_MODEL = "gpt-6-luna"
GROUP_EFFORT = "low"
GROUP_PROMPT_VERSION = "group-v1"
GROUP_EXAMPLES_PER_ISSUE = 12

# --- Memo role (one call over saved aggregates + bounded evidence pack) ---
MEMO_MODEL = "gpt-6.1-sol"
MEMO_EFFORT = "low"
MEMO_PROMPT_VERSION = "memo-v3"  # v2: explain volume spikes; v3 (2026-10-08): robustness + first-steps sections
MEMO_TOP_ISSUES = 8
MEMO_MAX_OUTPUT_TOKENS = 8000

# --- Controls ---------------------------------------------------------------
MAX_API_ATTEMPTS = 3              # transient API errors (rate limit, 5xx, timeout) per request
MAX_INVALID_OUTPUT_RETRIES = 1    # course rule: retry invalid output once, then quarantine

TOPICS = ["access", "usability", "playback", "downloads", "catalog", "billing", "support", "other"]
INTENTS = ["cancellation", "complaint", "request", "praise", "unclear"]
SENTIMENTS = [-1, -0.5, 0, 0.5, 1]


def call_cost(model, input_tokens, cached_tokens, output_tokens):
    """Billed cost of one call. Cached input is a separate, cheaper billing item;
    reasoning tokens are already included in output_tokens, so they are not added again."""
    r = RATES[model]
    uncached = input_tokens - cached_tokens
    return (uncached * r["input"] + cached_tokens * r["cached_input"] + output_tokens * r["output"]) / 1_000_000
