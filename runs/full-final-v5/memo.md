# Recommendation
Prioritize **usability** next quarter, attacking ISS-usability-ads (Too Many Interruptive Ads) and ISS-usability-shuffle_skip_limits (Shuffle and Skip Restrictions) first. Focus on interruption frequency and predictable playback control, while distinguishing intentional free-tier restrictions from defects before choosing changes.

## Why this area
Usability has the largest complaint volume and severity total among the eligible areas: 81280 complaint records, 27.4% of complaints, and aggregate severity of 206128. This makes it the strongest area-level choice under the pack’s severity-weighted ranking.

The actionable priorities are:
- **ISS-usability-ads — Too Many Interruptive Ads:** 35283 complaints [C009], mean severity 2.198027 [C011], and priority score 77553 [C012].
- **ISS-usability-shuffle_skip_limits — Shuffle and Skip Restrictions:** 14513 complaints [C013], mean severity 2.943086 [C015], and priority score 42713 [C016].

Ads supply the larger volume signal; shuffle and skip restrictions carry greater mean severity. Together, they point toward improving listening continuity and control rather than a broad navigation redesign. Start with diagnosing consecutive interruptions, repeat-track experiences, and unclear control availability; the evidence does not establish which implementation would resolve them.

## Alternatives considered
**Billing/support** is the closest alternative. ISS-billing-basic_features_paywalled (Basic Features Behind Premium) has 29166 complaints [C005], mean severity 2.807207 [C007], and priority score 81875 [C008]—higher than either selected usability issue individually. However, the area totals are lower: 52582 complaint records and aggregate severity 149237. Its complaint share rose from 11.1% to 20.6% across the comparable windows. Evidence that entitlement changes are commercially viable could shift the decision toward billing/support.

**Playback** has 45844 complaint records and aggregate severity 151675. ISS-playback-crashes_wont_open (Crashes and App Won’t Open) is more severe per complaint: 7779 complaints [C025], mean severity 3.588508 [C027], and priority score 27915 [C028]. Reliability remains important, but its measured burden is lower; evidence of widespread listening-blocking failures would change that judgment.

**Access** has the smallest measured burden: 10186 complaint records and aggregate severity 39433. Outside-area complaints are substantial, but include nonspecific complaints and event concentrations that do not identify a clear product intervention.

## Representative customer evidence
- “there are too many ads” (92bd7ff4-4322-4406-9033-f13e3079aa74)
- “ads after every song” (63eb97a3-0e84-4b30-9d8f-b0ba12cfc853)
- “No option for turn off shuffle” (ae776e66-d026-4313-a3d9-c7f5c34c4f6f)

## Limitations
These are self-selected public reviews, not representative customer prevalence. The pack contains no revenue, plan, or churn data; cancellation labels capture expressed intent, not observed cancellation. Ranking assigns one issue per complaint and uses severity sum, not expected business impact. Related free-tier complaints span usability and billing/support, making taxonomy boundaries consequential.

Verification covered 2000 records: intent agreement was 0.944, topic agreement 0.8665, severity agreement 0.899, and severity MAE 0.1135. Label error therefore remains. Of 660622 source rows, 22 were unresolved: 9 quarantined for invalid model output after retry and 13 for empty review text. Review volume varies over time, and event-driven spikes limit causal interpretation.