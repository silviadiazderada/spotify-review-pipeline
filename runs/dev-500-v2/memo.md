# Recommendation
Prioritize **usability** next quarter, attacking ISS-usability-ads (Excessive and Unskippable Ads) first, followed by ISS-usability-shuffle_skip_limits (Shuffle and Skip Restrictions). Focus on ad interruptions and understandable playback controls, distinguishing intended restrictions from confusing behavior before choosing changes.

## Why this area
Usability has the strongest aggregate signal among the eligible areas: 70 complaint records, 28.7% of complaints, and severity sum 176. This supports a concentrated usability effort rather than distributing work across unrelated problems.

ISS-usability-ads leads the actionable issue ranking with 31 complaints [C005], mean severity 2.193548 [C007], and priority score 68 [C008]. Customers describe ads displacing music and appearing consecutively. Investigating interruption frequency and sequencing should therefore lead the quarter’s work.

ISS-usability-shuffle_skip_limits follows with 15 complaints [C013], mean severity 2.933333 [C015], and priority score 44 [C016]. Its higher mean severity strengthens the case for addressing customers’ difficulty controlling song selection and playback alongside ads.

ISS-usability-redesign_ui (Confusing Interface and Removed Features) provides a secondary usability backlog: 11 complaints [C025], mean severity 2.727273 [C027], and priority score 30 [C028]. Keep navigation and removed-feature concerns in scope for diagnosis, without diluting the initial focus.

## Alternatives considered
**Playback** has 45 complaint records and severity sum 159. ISS-playback-crashes_wont_open (App Crashes and Loading Failures) is serious: 8 complaints [C021], mean severity 3.750000 [C023], and priority score 30 [C024]. Evidence that these failures affect a broader population would justify moving reliability ahead of usability.

**Billing/support** has 43 complaint records and severity sum 128. ISS-billing-basic_features_paywalled (Basic Features Behind Premium) contributes 18 complaints [C009], mean severity 2.833333 [C011], and priority score 51 [C012]. It ranks lower at area level; plan and commercial evidence could change that assessment.

**Access** has 8 complaint records and severity sum 30, giving it the smallest observed signal.

ISS-other-general (Mixed Generic App Complaints) has the highest individual priority score, 126 [C004], but sits outside the eligible areas and lacks a consistent specific defect. Diagnose it rather than treating it as a coherent delivery target.

## Representative customer evidence
- “always plays adds instead of songs” (cf6166ae-d71a-4839-9add-088645ad3b78)
- “will not let you go to any random song in a playlist while on mobile” (08d3a5a9-1ec1-4b10-a5c8-393da33843e1)
- “every update they make seems to make the app LESS user friendly” (0070e713-4cb7-4d78-954f-1764d5593c91)

## Limitations
These are self-selected public reviews, not representative usage measurements. The pack contains no revenue, plan, or churn data; cancellation reflects expressed intent, not confirmed churn.

Ranking uses complaint count multiplied by mean severity and assigns each complaint a single issue. Verification covered 96 records: agreement was 0.9688 for intent, 0.8542 for topic, and 0.9062 for severity; severity MAE was 0.1042. Labels therefore retain uncertainty. All 500 classifications were completed, with 0 unclassified records; broad, diagnostically unresolved complaints nevertheless remain.