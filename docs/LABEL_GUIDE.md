# Label guide (shared definitions + our examples)

Source of the definitions: `GRADING_CONTRACT.md` (course common labels). The examples below are **invented by us** for illustration. None of them come from the golden 50, because golden labels must never reach a prompt.

Label the **text only**. Ignore the stars: a 1-star "Good" is still praise.

## 1. Intent: what is the person doing?

Check the options **in this order** and stop at the first one that fits:

| Order | Intent | Use when… | Example |
|---|---|---|---|
| 1 | `cancellation` | They say they're leaving, uninstalling or cancelling, or threaten to | "Uninstalling, the shuffle is useless" |
| 2 | `complaint` | A negative experience, including mixed praise + criticism, or a generic "bad app" | "Love the music but the ads are nonstop" |
| 3 | `request` | They want a change but report nothing broken | "Please add a sleep timer for podcasts" |
| 4 | `praise` | Positive and nothing else | "Best music app ever" |
| 5 | `unclear` | Meaningless, unrelated, or a bare boycott slogan without a product complaint | "hello", "#BoycottSpotify" |

## 2. Topic: what is it about?

Choose **one**. If several problems are mentioned, choose the **most severe**. If they tie, choose the **first one mentioned**. For praise, choose the first specific feature praised. General praise ("great app") is `other`.

| Topic | Covers | Example |
|---|---|---|
| `access` | Login, signup, password, account access | "Can't log in since the update" |
| `usability` | Navigation, controls, layout, queue/playlist management, **ads** | "Too many ads between songs" |
| `playback` | Won't play, crashes, lag, connection errors, audio quality, battery/data use | "App crashes every time I open it" |
| `downloads` | Downloading, saved/offline music, downloads disappearing | "My downloaded songs vanished" |
| `catalog` | Missing songs/artists, search, recommendations, lyrics | "Lyrics are gone for most songs" |
| `billing` | Price, charges, subscriptions, paywalls, Premium-only features | "Charged twice this month" / "Can't pick songs without Premium" |
| `support` | Contacting support and their response | "Support never answered my email" |
| `other` | General praise/criticism, unrelated content, nothing specific | "Great app", "Worst app" |

Common traps:
- **Merely mentioning Premium does not make it `billing`.** "I pay for Premium and it keeps crashing" → `playback`.
- **Ads count as `usability`**, unless the review is about paying to remove them, which is `billing`.
- **"Bad app" with no detail** is a `complaint` with topic `other`. Don't guess the defect.

## 3. Severity: how bad is the reported impact? (1–5)

| Level | Meaning | Example |
|---|---|---|
| 1 | No problem: praise, neutral/unclear, or a pure feature request | "Love it", "Add a dark mode please" |
| 2 | Dislike, generic criticism, annoyance, cosmetic; no function lost | "Worst app", "Too many ads" |
| 3 | A function degraded or restricted, but some use remains | "Shuffle keeps repeating the same 10 songs" |
| 4 | A core task is clearly **blocked** | "Can't log in at all", "No song will play" |
| 5 | Explicit serious **financial, privacy or data** harm | "Charged $60 after cancelling", "My account was hacked and my playlists deleted" |

Angry words, many emojis or "I'm cancelling" do **not** by themselves raise severity.

## 4. Sentiment: overall tone (−1 to 1)

`-1` very negative · `-0.5` negative · `0` neutral or mixed · `0.5` positive · `1` very positive

## 5. Needs review (yes/no)

Choose `yes` if you honestly can't decide: missing context, two labels equally valid, or a language you can't read. Write why in **notes**.

## 6. Evidence quote (optional for the golden set)

The shortest exact piece of the review that justifies your label. For short reviews, the whole text is fine.
