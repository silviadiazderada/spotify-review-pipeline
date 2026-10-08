# Memo audit (independent recomputation)

Memo: `runs/full-final-v7/memo.md`. Recomputed from `grading/records.jsonl.gz`, `grading/membership.csv`, `data/raw/spotify_reviews_18months.csv` and `verify_comparisons.csv`, without the pipeline database or any model call.

- Numbers in memo: **63**, traced and correct: **63**
- claims.csv rows matching recomputed issue metrics: **32/32**
- Evidence-pack fields matching recomputation: **42/42**
- Quoted reviews found verbatim: **3/3**
- Problems: **0**

## Every number

| Number | Context | Traced to | Independent value | OK |
|---|---|---|---|---|
| 81280 | …ility leads the baseline decision areas with 81280 complaint/cancellat… | area[usability].complaint_records, robustness[complaint_count_only].usability | 81280 | ✓ |
| 27.4 | …s with 81280 complaint/cancellation records, 27.4% of complaints, and… | area[usability].share_of_complaints | 27.4% | ✓ |
| 206128 | …cords, 27.4% of complaints, and severity sum 206128. Playback totals 45… | area[usability].severity_sum, robustness[baseline_severity_sum].usability | 206128 | ✓ |
| 45844 | …ts, and severity sum 206128. Playback totals 45844 records and severit… | area[playback].complaint_records, robustness[complaint_count_only].playback | 45844 | ✓ |
| 151675 | …ayback totals 45844 records and severity sum 151675; billing/support to… | area[playback].severity_sum, robustness[baseline_severity_sum].playback, robustness[free_tier_restrictions_counted_as_billing].playback | 151675 | ✓ |
| 52582 | …severity sum 151675; billing/support totals 52582 and 149237; access… | area[billing/support].complaint_records, robustness[complaint_count_only].billing/support | 52582 | ✓ |
| 149237 | …sum 151675; billing/support totals 52582 and 149237; access totals 1018… | area[billing/support].severity_sum, robustness[baseline_severity_sum].billing/support | 149237 | ✓ |
| 10186 | …pport totals 52582 and 149237; access totals 10186 and 39433. The act… | area[access].complaint_records, robustness[complaint_count_only].access | 10186 | ✓ |
| 39433 | …ls 52582 and 149237; access totals 10186 and 39433. The actionable us… | area[access].severity_sum, robustness[baseline_severity_sum].access, robustness[free_tier_restrictions_counted_as_billing].access | 39433 | ✓ |
| 35283 | …Too Many Interruptive Ads:** complaint count 35283 [C009], mean severi… | claim C009: ISS-usability-ads complaint_count | 35283 | ✓ |
| 2.198027 | …complaint count 35283 [C009], mean severity 2.198027 [C011], priority sc… | claim C011: ISS-usability-ads mean_severity | 2.198027 | ✓ |
| 77553 | …ean severity 2.198027 [C011], priority score 77553 [C012]. - **ISS-usa… | claim C012: ISS-usability-ads priority_score | 77553 | ✓ |
| 14513 | …fle and Skip Restrictions:** complaint count 14513 [C013], mean severi… | claim C013: ISS-usability-shuffle_skip_limits complaint_count | 14513 | ✓ |
| 2.943086 | …complaint count 14513 [C013], mean severity 2.943086 [C015], priority sc… | claim C015: ISS-usability-shuffle_skip_limits mean_severity | 2.943086 | ✓ |
| 42713 | …ean severity 2.943086 [C015], priority score 42713 [C016]. - **ISS-usa… | claim C016: ISS-usability-shuffle_skip_limits priority_score | 42713 | ✓ |
| 10164 | …ixed Usability Complaints:** complaint count 10164 [C029], mean severi… | claim C029: ISS-usability-general complaint_count | 10164 | ✓ |
| 2.554211 | …complaint count 10164 [C029], mean severity 2.554211 [C031], priority sc… | claim C031: ISS-usability-general mean_severity | 2.554211 | ✓ |
| 25961 | …ean severity 2.554211 [C031], priority score 25961 [C032]. This mixed… | claim C032: ISS-usability-general priority_score | 25961 | ✓ |
| 4 | …How robust is this choice Usability leads **4 of 6** scenarios: b… | robustness.scenarios_led_by_usability | 4 | ✓ |
| 6 | …robust is this choice Usability leads **4 of 6** scenarios: baseli… | robustness.scenarios_total | 6 | ✓ |
| 98180 | …w_May_Oct_2023:** billing/support leads with 98180 versus usability 88… | robustness[latest_window_May_Oct_2023].billing/support | 98180 | ✓ |
| 88957 | …ng/support leads with 98180 versus usability 88957, playback 49395, and… | robustness[latest_window_May_Oct_2023].usability | 88957 | ✓ |
| 49395 | …with 98180 versus usability 88957, playback 49395, and access 22154. -… | robustness[latest_window_May_Oct_2023].playback | 49395 | ✓ |
| 22154 | …usability 88957, playback 49395, and access 22154. - **free_tier_rest… | robustness[latest_window_May_Oct_2023].access | 22154 | ✓ |
| 191950 | …ted_as_billing:** billing/support leads with 191950 versus usability 16… | robustness[free_tier_restrictions_counted_as_billing].billing/support | 191950 | ✓ |
| 163415 | …g/support leads with 191950 versus usability 163415, playback 151675, an… | robustness[free_tier_restrictions_counted_as_billing].usability | 163415 | ✓ |
| 151675 | …ith 191950 versus usability 163415, playback 151675, and access 39433.… | area[playback].severity_sum, robustness[baseline_severity_sum].playback, robustness[free_tier_restrictions_counted_as_billing].playback | 151675 | ✓ |
| 39433 | …sability 163415, playback 151675, and access 39433. The area choice t… | area[access].severity_sum, robustness[baseline_severity_sum].access, robustness[free_tier_restrictions_counted_as_billing].access | 39433 | ✓ |
| 90377 | …trictions theme is more stable conceptually: 90377 records, severity s… | theme[free_tier_experience_ads_plus_restrictions].complaint_records | 90377 | ✓ |
| 236515 | …le conceptually: 90377 records, severity sum 236515, and 30.4% of compla… | theme[free_tier_experience_ads_plus_restrictions].severity_sum | 236515 | ✓ |
| 30.4 | …lly: 90377 records, severity sum 236515, and 30.4% of complaints. Its… | theme[free_tier_experience_ads_plus_restrictions].share_of_complaints | 30.4% | ✓ |
| 29166 | …eatures Behind Premium — has complaint count 29166 [C005], mean severi… | claim C005: ISS-billing-basic_features_paywalled complaint_count | 29166 | ✓ |
| 2.807207 | …complaint count 29166 [C005], mean severity 2.807207 [C007], and priorit… | claim C007: ISS-billing-basic_features_paywalled mean_severity | 2.807207 | ✓ |
| 81875 | …severity 2.807207 [C007], and priority score 81875 [C008]. ISS-billing… | claim C008: ISS-billing-basic_features_paywalled priority_score | 81875 | ✓ |
| 11415 | …ntrols Require Premium — has complaint count 11415 [C017], mean severi… | claim C017: ISS-billing-premium_only_controls complaint_count | 11415 | ✓ |
| 3.011301 | …complaint count 11415 [C017], mean severity 3.011301 [C019], and priorit… | claim C019: ISS-billing-premium_only_controls mean_severity | 3.011301 | ✓ |
| 34374 | …severity 3.011301 [C019], and priority score 34374 [C020]. It ranks lo… | claim C020: ISS-billing-premium_only_controls priority_score | 34374 | ✓ |
| 7779 | …hes and App Won’t Open — has complaint count 7779 [C025], mean severi… | claim C025: ISS-playback-crashes_wont_open complaint_count | 7779 | ✓ |
| 3.588508 | …s complaint count 7779 [C025], mean severity 3.588508 [C027], and priorit… | claim C027: ISS-playback-crashes_wont_open mean_severity | 3.588508 | ✓ |
| 27915 | …severity 3.588508 [C027], and priority score 27915 [C028]. Independent… | claim C028: ISS-playback-crashes_wont_open priority_score | 27915 | ✓ |
| 3.4 | …cess** has the smallest aggregate burden, at 3.4% of complaints. Evi… | area[access].share_of_complaints, trend[May-Oct 2023].share[access] | 3.4% | ✓ |
| 2000 | …gns one issue per complaint. Verification of 2000 records found agree… | verify.verified | 2000 | ✓ |
| 0.944 | …ification of 2000 records found agreement of 0.944 for intent, 0.8665… | verify.agreement_intent | 0.944 | ✓ |
| 0.8665 | …records found agreement of 0.944 for intent, 0.8665 for topic, and 0.89… | verify.agreement_topic | 0.8665 | ✓ |
| 0.899 | …t of 0.944 for intent, 0.8665 for topic, and 0.899 for severity, with… | verify.agreement_severity | 0.899 | ✓ |
| 0.1135 | …c, and 0.899 for severity, with severity MAE 0.1135. Of 660622 source r… | verify.severity_mae | 0.1135 | ✓ |
| 660622 | …9 for severity, with severity MAE 0.1135. Of 660622 source rows, 22 rem… | scope.source_rows | 660622 | ✓ |
| 22 | …severity MAE 0.1135. Of 660622 source rows, 22 remain unclassified… | scope.unclassified | 22 | ✓ |
| 9 | …660622 source rows, 22 remain unclassified: 9 invalid outputs aft… | scope.quarantined_invalid_output | 9 | ✓ |
| 13 | …lassified: 9 invalid outputs after retry and 13 empty texts. Volum… | scope.quarantined_empty_text | 13 | ✓ |
| 46.4 | …ater comparable window’s outside-area share: 46.4% versus 17.0% earli… | trend[May-Oct 2023].share[outside the four areas] | 46.4% | ✓ |
| 17.0 | …le window’s outside-area share: 46.4% versus 17.0% earlier. Jul 6-9 2… | trend[Jun-Nov 2022].share[outside the four areas] | 17.0% | ✓ |
| 6 | …-area share: 46.4% versus 17.0% earlier. Jul 6-9 2023 contains 365… | robustness.scenarios_total | 6 | ✓ |
| 9 | …rea share: 46.4% versus 17.0% earlier. Jul 6-9 2023 contains 36509… | scope.quarantined_invalid_output | 9 | ✓ |
| 2023 | …a share: 46.4% versus 17.0% earlier. Jul 6-9 2023 contains 36509 revi… | calendar year | 2023 | ✓ |
| 36509 | …versus 17.0% earlier. Jul 6-9 2023 contains 36509 reviews and 24494 o… | spike[Jul 6-9 2023].reviews | 36509 | ✓ |
| 24494 | …ier. Jul 6-9 2023 contains 36509 reviews and 24494 outside-area compla… | spike[Jul 6-9 2023].outside_area_complaints | 24494 | ✓ |
| 3020 | …9 reviews and 24494 outside-area complaints; 3020 keyword matches are… | spike[Jul 6-9 2023].boycott_keyword_reviews | 3020 | ✓ |
| 2023 | …ent with boycott-related review bombing. Oct 2023 contains 26095 outs… | calendar year | 2023 | ✓ |
| 26095 | …tt-related review bombing. Oct 2023 contains 26095 outside-area compla… | spike[Oct 2023].outside_area_complaints | 26095 | ✓ |
| 41.1 | …2023 contains 26095 outside-area complaints; 41.1% mention update/ver… | spike[Oct 2023].share_mentioning_update | 41.1% | ✓ |
| 12.6 | …plaints; 41.1% mention update/version versus 12.6% in Jan-Jun 2023, c… | spike[Jan-Jun 2023].share_mentioning_update | 12.6% | ✓ |
| 2023 | …ntion update/version versus 12.6% in Jan-Jun 2023, consistent with non… | calendar year | 2023 | ✓ |

## Quoted reviews

| Review ID | Quote | Issue | Verbatim |
|---|---|---|---|
| `92bd7ff4-4322-4406-9033-f13e3079aa74` | there are too many ads | `ISS-usability-ads` | ✓ |
| `ae776e66-d026-4313-a3d9-c7f5c34c4f6f` | No option for turn off shuffle | `ISS-usability-shuffle_skip_limits` | ✓ |
| `5332a9f1-d7ff-4062-ad9f-47cd3cc7bacc` | If you want to rewind the song, you have to use premium | `ISS-billing-premium_only_controls` | ✓ |
