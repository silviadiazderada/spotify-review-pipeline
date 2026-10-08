# Recommendation
Prioritize **usability** next quarter, attacking disruptive and repetitive ads (ISS-usability-ads) first, followed by shuffle, repeat, and skip limits (ISS-usability-shuffle_skip_limits). Focus on interruptions that prevent listening and unclear or unwanted playback controls, while distinguishing defects from intentional product restrictions.

## Why this area
Usability leads the eligible decision areas with 1263 complaint records, 27.8% of complaints, and an aggregate severity sum of 3154. It offers the strongest combination of complaint volume and severity-weighted burden.

Disruptive and Repetitive Ads (ISS-usability-ads) is the highest-ranked issue within the eligible areas: complaint count 571 [C005], mean severity 2.190893 [C007], and priority score 1251 [C008]. Reports describe interruptions severe enough to make the app unusable. Start by investigating ad interruptions and failure states rather than assuming all dissatisfaction requires changing ad policy.

Shuffle, Repeat, and Skip Limits (ISS-usability-shuffle_skip_limits) adds complaint count 194 [C021], mean severity 2.902062 [C023], and priority score 563 [C024]. General App Usability Problems (ISS-usability-general) reinforces the broader control problem, with complaint count 188 [C029], mean severity 2.542553 [C031], and priority score 478 [C032]. Together, these issues support a focused listening-control agenda rather than an undirected interface redesign.

## Alternatives considered
**Billing/support** is the closest alternative: 856 complaint records and aggregate severity sum 2452. Subscription Required for Playback (ISS-billing-general) has complaint count 293 [C009], mean severity 2.764505 [C011], and priority score 810 [C012]. Basic Features Require Premium (ISS-billing-basic_features_paywalled) has complaint count 258 [C013], mean severity 2.937984 [C015], and priority score 758 [C016]. These warrant attention, but the pack cannot distinguish entitlement defects, policy dissatisfaction, and misunderstanding reliably enough to recommend a monetization change.

**Playback** has 702 complaint records and aggregate severity sum 2325. Mixed General Playback Problems (ISS-playback-general) is more severe on average: complaint count 202 [C017], mean severity 3.326733 [C019], and priority score 672 [C020]. **Access** has 155 complaint records and aggregate severity sum 594. Both rank below usability on total burden; evidence of concentrated listening failures or disproportionate business impact could change that decision.

Mixed General App Complaints (ISS-other-general), outside the eligible areas, has priority score 2643 [C004]. Its heterogeneous content warrants diagnostic triage, not reassignment wholesale to usability.

## Representative customer evidence
- “Makes the app unusable.” (933b1cf2-8fa9-46aa-9a06-85fd89533a99)
- “it will only give me random songs” (25bbe898-e819-4fcb-942b-0fccd065a33f)
- “now you can't even go to a specific length of a song” (79bfe0dc-2854-4cbd-b6a0-a89936f2a14f)

## Limitations
These are self-selected public reviews, not a representative customer survey. There is no revenue, plan, or churn data; cancellation is expressed intent, not confirmed churn. Ranking uses complaint count multiplied by mean severity, equivalent to severity sum, with a single issue assigned per complaint.

Verification covered 1680 records: agreement was 0.9512 for intent, 0.8982 for topic, and 0.9149 for severity; severity MAE was 0.0917. Label error and overlapping themes may affect prioritization. Of 10000 source rows, 9949 were classified; 51 remain unresolved and quarantined after invalid model output on retry.