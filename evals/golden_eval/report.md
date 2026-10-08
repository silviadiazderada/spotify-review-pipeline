# Golden-50 evaluation

Predictions: `state/golden.sqlite` (label_config `gpt-6-luna+effort-none+enrich-v1+schema-v1`). Human labels: `evals/golden_50_human.csv`. Missing or quarantined predictions count as incorrect.

| Field | Result |
|---|---|
| Intent agreement | 84% (macro F1 0.7292) |
| Topic agreement | 70% (macro F1 0.3788) |
| Severity exact agreement | 74% (MAE 0.32) |
| Sentiment within ±0.5 | 92% (MAE 0.34) |
| Evidence quote exact substring | 50/50 (0 replaced by full text in code) |
| needs_review | human 10, model 7, both 0 |

**Secondary, rule-adjusted reference (disclosed, adjudicated after predictions were seen; 10 cases, see `evals/golden_rule_adjustments.csv`):** intent 90%, topic 84%, severity 76%. Primary results above use the original frozen human labels.

## Intent confusion

| human \ model | cancellation | complaint | request | praise | unclear |
|---|---|---|---|---|---|
| **cancellation** | 1 | 2 |  |  |  |
| **complaint** |  | 15 |  | 1 |  |
| **request** |  | 1 | 1 |  |  |
| **praise** |  |  |  | 20 |  |
| **unclear** |  | 4 |  |  | 5 |

## Topic confusion

| human \ model | access | usability | playback | downloads | catalog | billing | other |
|---|---|---|---|---|---|---|---|
| **access** |  |  | 1 |  |  |  |  |
| **usability** |  | 2 | 1 |  | 2 |  |  |
| **playback** |  | 1 | 2 |  |  |  |  |
| **downloads** |  |  |  |  |  |  |  |
| **catalog** |  |  |  |  | 2 |  | 1 |
| **billing** |  | 5 |  | 1 |  | 2 | 1 |
| **other** |  | 1 |  |  | 1 |  | 27 |

## Disagreements

| # | Text (first 100 chars) | Human (intent/topic/sev) | Model | Human note |
|---|---|---|---|---|
| 1 | Staff must be full of mentally ill kool-aid heads. Banning conservative music that speaks truth. Spo | complaint/catalog/2 | complaint/catalog/3 |  |
| 4 | Ads were okay, but limited functionality..it's just too much | complaint/billing/2 | complaint/usability/2 |  |
| 10 | Duo Premium .... No ads at all! | complaint/billing/2 | praise/other/1 |  |
| 12 | Update: I reached out to Spotify Support and with some help from Sarah I was able to get the app wor | complaint/usability/3 | complaint/playback/4 |  |
| 16 | I like it but god I hate it when the music Interrupts my ads | complaint/billing/2 | complaint/usability/2 |  |
| 19 | asem, lirik nya kdang gaada kek mana?? | unclear/other/1 | complaint/catalog/3 |  |
| 22 | I LOVE that I was able to put in only a few songs I like and Spotify gave me recommendations for an  | praise/usability/1 | praise/catalog/1 |  |
| 24 | Please ye ads ko thoda kumm Karo harr ek song ke baad ad 🙏🙄 | request/billing/1 | complaint/usability/2 |  |
| 29 | Deleting this App. The new update suck, we can't choose our fvrt songs after some clicks, we can't C | cancellation/billing/4 | cancellation/usability/3 |  |
| 30 | It's my best music app but now it's not...everything basic features is premium.... | unclear/billing/1 | complaint/billing/3 |  |
| 31 | I hate this app and sweden .I love islam | unclear/other/1 | complaint/other/2 |  |
| 32 | What is happening with Spotify?? Recently I'm trying to play a song but it doesn't working. So I uns | complaint/access/4 | complaint/playback/4 |  |
| 33 | Are you out of your mind? This is dangerous! Listening to music in a normal volume and suddenly an a | complaint/playback/3 | complaint/usability/5 |  |
| 37 | Nice app, very less advertising | praise/billing/1 | praise/usability/1 |  |
| 38 | 1-Lyrics not getting loaded, 2-can't go back to or start song where to wanted. Pathetic update | complaint/usability/4 | complaint/catalog/3 |  |
| 42 | Worst application 👎👎👎 | unclear/other/1 | complaint/other/2 |  |
| 45 | paying for subscribing but unable to play in offline mode really? | complaint/billing/2 | complaint/downloads/3 |  |
| 46 | Worst app ever too much ad | complaint/other/2 | complaint/usability/2 |  |
| 47 | Too expensive and the free version is pretty much unusable with constant ads... Every two or three s | cancellation/billing/2 | complaint/billing/3 |  |
| 48 | This update very bad for everyone.old Spotify. we all want. | cancellation/other/2 | complaint/other/2 |  |
| 50 | best app ever | praise/catalog/1 | praise/other/1 |  |
