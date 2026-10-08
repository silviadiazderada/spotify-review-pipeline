# Golden-50 error analysis (prompt `enrich-v1`)

**Status:** categories were drafted with AI assistance and reviewed by Silvia on 2026-10-07. She accepted the category-B finding: in those cases her original label departed from the written contract. The original frozen labels stay as the primary reference. A rule-adjusted reference for 10 of the 11 B cases is reported only as a secondary, disclosed diagnostic. Case 19 is excluded because no rule decides it. Adjustments are listed in `evals/golden_rule_adjustments.csv`: intent 90%, topic 84%, severity 76%.

The golden labels were frozen before any prediction (`evals/golden_50_human.csv`, see D4). They were **not** changed after seeing model output. Changing them now would bias the evaluation toward the model.

## Headline numbers

| Field | Result |
|---|---|
| Intent | 84% agreement |
| Topic | 70% agreement |
| Severity | 74% exact agreement, MAE 0.32 |
| Sentiment | 92% within ±0.5 |
| Evidence quotes | 50/50 exact substrings |

Full numbers are in `report.md`. With n=50 these are diagnostics, not population accuracy estimates.

## The 21 disagreements, by cause

### A. Model contradicts the written rules: clear model errors (2)

| # | Review (short) | Human | Model | Rule that decides |
|---|---|---|---|---|
| 33 | "suddenly an ad starts and my ears feel like they explode… dangerous" | complaint/playback/3 | complaint/usability/**5** | Severity 5 requires explicit financial, privacy or data harm; "angry language alone is insufficient". Model over-escalated on the word "dangerous". |
| 29 | "can't choose songs… can't turn off shuffle… pushing us to upgrade to Premium… deleting this app" | cancellation/**billing**/4 | cancellation/usability/3 | "Explicitly premium-only controls go here (billing)". The review explicitly ties the lost controls to Premium. |

### B. Human label departs from the written rules; model follows them (11)

| # | Review (short) | Human | Model | Rule |
|---|---|---|---|---|
| 16 | "music interrupts my ads" (joke about ads) | billing | usability | Ads are usability unless about paying to remove them |
| 37 | "very less advertising" | billing | usability | Same |
| 46 | "Worst app ever too much ad" | other | usability | Same |
| 22 | "gave me recommendations…" (praise) | usability | catalog | Recommendations are catalog |
| 32 | "trying to play a song but it doesn't work" | access | playback | Playback failure is playback |
| 45 | "paying… but unable to play in offline mode" | billing | downloads | A paid-plan mention alone is not billing; offline is downloads |
| 42 | "Worst application 👎" | unclear/1 | complaint/2 | Generic "bad app" is a complaint (severity 2) |
| 30 | "now it's not… everything basic is premium" | unclear/1 | complaint/3 | Negative experience is a complaint |
| 48 | "This update very bad… old Spotify we all want" | cancellation | complaint | Cancellation needs explicit departure |
| 50 | "best app ever" | catalog | other | General praise is other |
| 19 | Indonesian: "the lyrics are sometimes missing?" | unclear | complaint/catalog | The model read the language; the human labeler could not |

**Pattern:** the human labeler treated **ads as a billing issue**, because Premium removes ads (3 cases). That is a real business intuition, but the shared taxonomy files ads under usability. The memo should note that the ads and free-tier-restriction themes span both areas.

### C. Genuinely ambiguous: both labels defensible (8)

| # | Why it is ambiguous |
|---|---|
| 1 | Political complaint about removed songs. Catalog is agreed; severity 2 vs 3 depends on whether removal is a "restriction". |
| 4 | "Ads okay, but limited functionality": paywall (billing) or ads (usability)? |
| 10 | "Duo Premium…. No ads at all!" (5 stars): sincere praise or sarcasm? |
| 12 | Crash report later resolved by support: playback/4 at the time vs resolved now. |
| 24 | Hindi "please reduce the ads after every song": request or complaint? |
| 31 | "I hate this app and Sweden…": boycott slogan (unclear) or generic complaint? |
| 38 | Two problems with equal severity (lyrics, seeking). The rule picks the first mentioned (lyrics → catalog); the human picked the second. |
| 47 | "Too expensive… Forget it": "forget it" read as departure (human) or not explicit enough (model). |

## needs_review as a prediction

- The human flagged 10 cases and the model flagged 7. **No case was flagged by both.**
- So needs_review is **not** a reliable proxy for human uncertainty in this sample. We should not use it to route cases without further evidence.

## Implications

1. **Model errors to watch at scale:** severity inflation from alarming words (A-33), and Premium-restricted controls labeled usability instead of billing (A-29).
   - These are checked on the development data (`checkpoint_500`), **not** by tuning on these 50.
   - If the prompt is changed because of these findings, that will be disclosed, and fresh held-out cases will be labeled for the final check.
2. **Taxonomy ambiguity** (ads, free-tier restrictions) is a limitation to state in the memo. Totals for "billing" vs "usability" depend on this boundary.
