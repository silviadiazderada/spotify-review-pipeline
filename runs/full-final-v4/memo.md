# Recommendation
Prioritize **usability** next quarter, attacking ISS-usability-ads (Too Many Interruptive Ads) and ISS-usability-shuffle_skip_limits (Shuffle and Skip Restrictions) first. Focus on interruption frequency and playback control, while coordinating with billing owners where restrictions reflect Premium policy rather than interface defects.

## Why this area
Usability has the largest complaint burden among the eligible areas: 81280 complaint records, 27.4% of complaints, and aggregate severity of 206128. This supports prioritizing broad listening-experience friction rather than choosing solely by the most severe individual failure.

The leading actionable usability issue, ISS-usability-ads (Too Many Interruptive Ads), has complaint_count 35283 [C009], mean_severity 2.198027 [C011], and priority_score 77553 [C012]. ISS-usability-shuffle_skip_limits (Shuffle and Skip Restrictions) has complaint_count 14513 [C013], mean_severity 2.943086 [C015], and priority_score 42713 [C016]. Ads offer the larger volume opportunity; shuffle and skip restrictions carry greater average severity.

The ranking weights frequency by severity: priority_score equals severity_sum. It does not estimate commercial return or engineering effort. Treat this recommendation as a customer-friction priority, then validate specific interventions before committing to broad policy changes.

## Alternatives considered
**Billing/support** is the strongest alternative, with aggregate severity of 149237. ISS-billing-basic_features_paywalled (Basic Features Behind Premium) has complaint_count 29166 [C005], mean_severity 2.807207 [C007], and priority_score 81875 [C008], exceeding either proposed usability issue individually. Billing/support’s complaint share also rises from 11.1% to 20.6% across the comparable windows. However, usability leads on total burden. The cross-area free-tier restrictions theme represents 18.6% of complaints; evidence that entitlement policy dominates customer harm could shift the decision toward billing/support.

**Playback** has aggregate severity of 151675. ISS-playback-crashes_wont_open (Crashes and App Won’t Open) is more severe on average: complaint_count 7779 [C025], mean_severity 3.588508 [C027], and priority_score 27915 [C028]. Reliability warrants continued attention, but its area-wide burden is lower. Confirmed widespread service failure would change that judgment.

**Access** has 10186 complaint records and aggregate severity of 39433, placing it lower on the available evidence. Outside-area complaints account for 36.1%, so the eligible-area recommendation does not explain all dissatisfaction.

## Representative customer evidence
- “there are too many ads” (92bd7ff4-4322-4406-9033-f13e3079aa74)
- “ads after every song” (63eb97a3-0e84-4b30-9d8f-b0ba12cfc853)
- “No option for turn off shuffle” (ae776e66-d026-4313-a3d9-c7f5c34c4f6f)
- “cut down d basic feature of playing songs in order and limiting it to premium users” (9b42b7f8-2477-4516-b2de-6d46831fbad9)

## Limitations
These are self-selected public reviews, not representative customer incidence. No revenue, plan, or observed churn data are available; cancellation labels express intent, not confirmed departures. Verification covered 2000 records, with agreement of 0.944 for intent, 0.8665 for topic, and 0.899 for severity; severity MAE was 0.1135, indicating labeling uncertainty.

Classification completed for 660600 records; 22 remain unresolved, including 9 invalid-output quarantines and 13 empty-text quarantines. Each complaint receives a single issue, potentially obscuring overlapping problems. Comparable-window shares exclude partial boundary months, and varying review participation prevents causal interpretation of trends.