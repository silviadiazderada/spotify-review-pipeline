# Recommendation
Prioritize **usability** next quarter, attacking ISS-usability-ads (Excessive Unskippable Ads) and ISS-usability-general (Playback Controls and Shuffle Frustrations) first. Focus on disruptive ad sequences and predictable listening controls, while distinguishing usability defects from intentional premium restrictions before committing changes.

## Why this area
Usability has the largest complaint volume and severity burden among the eligible areas: 70 complaint records, representing 28.7% of complaint-and-cancellation records, with a severity sum of 176. This makes it the strongest area-level priority under the pack’s severity-weighted ranking approach.

The leading actionable usability issues are:
- **ISS-usability-ads — Excessive Unskippable Ads:** 24 complaints [C009], mean severity 2.208333 [C011], and priority score 53 [C012].
- **ISS-usability-general — Playback Controls and Shuffle Frustrations:** 21 complaints [C013], mean severity 2.428571 [C015], and priority score 51 [C016].
- **ISS-usability-redesign_ui — Redesign and Navigation Frustrations:** 16 complaints [C021], mean severity 2.812500 [C023], and priority score 45 [C024].

These descriptions suggest related listening-experience frustrations, but not a proven common cause. Start by separating ad interruptions, shuffle behavior, skip restrictions, and navigation problems into testable product questions. Treat redesign complaints as a supporting investigation rather than assuming another redesign is the remedy.

## Alternatives considered
**Playback** is the closest alternative: 45 complaint records and severity sum 159. ISS-playback-general (Music Playback Fails) has 14 complaints [C017], mean severity 3.571429 [C019], and priority score 50 [C020]. Its higher severity makes reliability important despite lower volume. Evidence that these failures are widespread or concentrated in current releases would shift the recommendation toward playback.

**Billing/support** has 43 complaint records and severity sum 128. ISS-billing-general (Premium Paywall Frustration) is the highest-ranked eligible individual issue, with 25 complaints [C005], mean severity 2.960000 [C007], and priority score 74 [C008]. However, it mixes objections to premium policy with broken purchase flows; those require different interventions. Confirmed purchase failures or commercial impact could change the decision.

**Access** has 8 complaint records and severity sum 30, making it the lowest aggregate priority. Outside the eligible areas, ISS-other-general (Mixed Generic App Complaints) leads with 61 complaints [C001] and priority score 126 [C004], but its broad description does not identify a coherent execution target.

## Representative customer evidence
- “The ads are really annoying and sometimes I get five one after the other” (b9ae23d2-1152-4bfe-a876-afc09c005377)
- “I only wish it wasn't limited on the skips” (ac581cea-24f2-4251-a062-53cdd77cfed7)
- “every update they make seems to make the app LESS user friendly” (0070e713-4cb7-4d78-954f-1764d5593c91)

## Limitations
These are self-selected public reviews, not representative customer incidence. The pack contains no revenue, plan, or churn data; cancellation is expressed intent, not observed churn. Priority scores equal severity sums, with one issue assigned per complaint, potentially obscuring overlap. Verification covered 96 records: intent agreement 0.9688, topic agreement 0.8542, severity agreement 0.9062, and severity MAE 0.1042 indicate label uncertainty. All 500 classifications were completed; 0 remained unclassified, although broad issue labels leave some product diagnoses unresolved.