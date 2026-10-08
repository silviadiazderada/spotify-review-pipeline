# Recommendation
Prioritize **usability**, attacking interruptive ads (ISS-usability-ads) and shuffle/skip restrictions (ISS-usability-shuffle_skip_limits) first. The robust core is dissatisfaction with the combined free-tier experience—ads and restricted controls—not an invariant win for the usability label across taxonomies and time windows.

## Why this area
Usability leads the baseline decision areas with 81280 complaint/cancellation records, 27.4% of complaints, and severity sum 206128. Playback totals 45844 records and severity sum 151675; billing/support totals 52582 and 149237; access totals 10186 and 39433.

The actionable usability leaders are:

- **ISS-usability-ads — Too Many Interruptive Ads:** complaint count 35283 [C009], mean severity 2.198027 [C011], priority score 77553 [C012].
- **ISS-usability-shuffle_skip_limits — Shuffle and Skip Restrictions:** complaint count 14513 [C013], mean severity 2.943086 [C015], priority score 42713 [C016].
- **ISS-usability-general — Mixed Usability Complaints:** complaint count 10164 [C029], mean severity 2.554211 [C031], priority score 25961 [C032]. This mixed category needs decomposition before prescribing changes.

Priority score equals complaint count multiplied by mean severity, or severity sum. This favors aggregate complaint burden rather than severity alone.

## How robust is this choice
Usability leads **4 of 6** scenarios: baseline severity sum, complaint count only, excluding spike events, and free-tier restrictions counted as usability. It does not lead in:

- **latest_window_May_Oct_2023:** billing/support leads with 98180 versus usability 88957, playback 49395, and access 22154.
- **free_tier_restrictions_counted_as_billing:** billing/support leads with 191950 versus usability 163415, playback 151675, and access 39433.

The area choice therefore depends on using the full review window and the baseline taxonomy, rather than emphasizing recent reviews or assigning shuffle/skip restrictions to billing.

The combined free-tier ads-plus-restrictions theme is more stable conceptually: 90377 records, severity sum 236515, and 30.4% of complaints. Its customer problem crosses the organizational boundary, so usability should coordinate with billing rather than interpret its lead as evidence against addressing paywalls.

## Alternatives considered
**Billing/support** is the strongest alternative. ISS-billing-basic_features_paywalled — Basic Features Behind Premium — has complaint count 29166 [C005], mean severity 2.807207 [C007], and priority score 81875 [C008]. ISS-billing-premium_only_controls — Playback Controls Require Premium — has complaint count 11415 [C017], mean severity 3.011301 [C019], and priority score 34374 [C020]. It ranks lower only under the baseline allocation; adopting recent-window weighting or the billing-oriented taxonomy would change the recommendation.

**Playback** ranks below usability in aggregate despite more severe individual failures. ISS-playback-crashes_wont_open — Crashes and App Won’t Open — has complaint count 7779 [C025], mean severity 3.588508 [C027], and priority score 27915 [C028]. Independently measured failure prevalence and reproducible outage evidence could justify prioritizing playback.

**Access** has the smallest aggregate burden, at 3.4% of complaints. Evidence of widespread blocked access or systematic underrepresentation in reviews would warrant reconsideration.

## What to do first
- For **ISS-usability-ads**, investigate ad frequency, consecutive placements, and interruption patterns; evaluate alternative pacing.
- For **ISS-usability-shuffle_skip_limits**, reproduce forced shuffle, repeated tracks, and skip limitations; distinguish intended entitlements from defects and evaluate clearer controls.
- Jointly review **ISS-billing-basic_features_paywalled** and **ISS-billing-premium_only_controls**: map expected versus available controls and evaluate entitlement messaging alongside restriction changes.

## Representative customer evidence
- “there are too many ads” (92bd7ff4-4322-4406-9033-f13e3079aa74)
- “No option for turn off shuffle” (ae776e66-d026-4313-a3d9-c7f5c34c4f6f)
- “If you want to rewind the song, you have to use premium” (5332a9f1-d7ff-4062-ad9f-47cd3cc7bacc)

## Limitations
These are self-selected public reviews, not representative customer incidence. There is no revenue, plan, or churn data; cancellation is expressed intent. Classification assigns one issue per complaint. Verification of 2000 records found agreement of 0.944 for intent, 0.8665 for topic, and 0.899 for severity, with severity MAE 0.1135. Of 660622 source rows, 22 remain unclassified: 9 invalid outputs after retry and 13 empty texts.

Volume spikes inflate the later comparable window’s outside-area share: 46.4% versus 17.0% earlier. Jul 6-9 2023 contains 36509 reviews and 24494 outside-area complaints; 3020 keyword matches are consistent with boycott-related review bombing. Oct 2023 contains 26095 outside-area complaints; 41.1% mention update/version versus 12.6% in Jan-Jun 2023, consistent with nonspecific update backlash. External causes are not established by these data, and keyword matches are a lower bound.