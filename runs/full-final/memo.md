# Recommendation
Prioritize **usability** next quarter, attacking unwanted playlist additions and unexpected song selection first: ISS-usability-ads (Unexpected Ads and Playlist Changes) and ISS-usability-shuffle_skip_limits (Shuffle Plays Unwanted Songs). Validate these mixed labels before committing fixes, then focus on making selected music and playlist behavior predictable.

## Why this area
Usability leads the eligible areas in both complaint volume and cumulative severity: 81280 complaint records, 27.4% of complaints, and a severity sum of 206128. This makes it the strongest area-level allocation signal, although not proof of business impact.

The leading actionable issue, ISS-usability-ads, has 39321 complaints [C005], mean severity 2.236871 [C007], and priority score 87956 [C008]. Its description combines ads with playlist changes, so the allocation should fund diagnosis rather than assume every record concerns advertising.

ISS-usability-shuffle_skip_limits adds 14436 complaints [C013], mean severity 2.944860 [C015], and priority score 42512 [C016]. Together, these issue descriptions point toward loss of control over what plays.

A secondary usability target is ISS-usability-redesign_ui (Update-Related Library and Interface Problems): 9005 complaints [C029], mean severity 2.631538 [C031], and priority score 23697 [C032]. Investigate unexpected changes to liked songs and missing playlists alongside the primary work, without assuming a common technical cause.

The ranking weights volume and severity: priority score equals severity sum. It does not estimate retention gains or implementation cost.

## Alternatives considered
**Billing/support** is the strongest alternative, with 52582 complaint records and severity sum 149237. ISS-billing-basic_features_paywalled (Unexpected or Duplicate Subscription Charges) has 29183 complaints [C009], mean severity 2.807593 [C011], and priority score 81934 [C012]. Confirmed charging failures merit attention; billing would become the priority if operational evidence established greater customer harm or business exposure.

**Playback** has 45844 complaint records and severity sum 151675, below usability overall. **Access** has 10186 complaint records and severity sum 39433. Either could supersede usability if incident evidence revealed concentrated, critical failures not reflected in review volume.

The largest aggregate category is outside the eligible areas, at 36.1% of complaints. Its prominence argues for parallel taxonomy investigation, not silently reallocating those records to usability.

## Representative customer evidence
- “STOP ADDING SONGS TO MY PLAYLIST!!!” (df87f280-77a2-4fb7-815f-a6b50d5f2beb)
- “this update automatically added all songs in my New Music playlist to my Liked Songs” (80e4d783-a1b7-476e-93cd-752a9e479513)
- “My subscription, although cancelled, still is hitting my account.” (b697b0d7-f49f-43e1-8fde-31ccecd894eb)

## Limitations
These are self-selected public reviews, not representative customer incidence. There is no revenue, plan, or churn data; cancellation is expressed intent, not observed churn. Verification covered 2000 records: agreement was 0.944 for intent, 0.8665 for topic, and 0.899 for severity; severity MAE was 0.1135. Mixed descriptions and mismatched examples warrant caution. Each complaint receives one issue, obscuring overlapping problems. Of 660622 source rows, 22 remain unclassified: 9 invalid model outputs after retry and 13 empty texts.