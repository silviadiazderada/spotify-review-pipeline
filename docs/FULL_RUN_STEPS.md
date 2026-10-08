# Full run with recorded interruption and resume

Run every command from the project folder:

```sh
cd ~/MBAClaude/FundamentalsAI/spotify-review-pipeline
```

## 0. Start the screen recording

Press `Cmd + Shift + 5`, choose **Record Entire Screen** (or Record Selected Portion around Terminal), then click **Record**.

## 1. Start the full run (phase "initial")

```sh
caffeinate -i uv run python -u -m pipeline.enrich --input data/raw/spotify_reviews_18months.csv --db state/full.sqlite --run-id full-initial --phase initial --workers 16 --budget-usd 30
```

Let it run for about 2 minutes. You will see batches completing: "batch N attempt 1: 50/50 valid, ok …".

## 2. Interrupt it

Press **Ctrl + C** once. The pipeline stops sending new requests, saves the answers already on the way, and prints a summary that includes `STOPPED: interrupted by user`.

## 3. Snapshot the saved work (checkpoint before)

```sh
uv run python -m pipeline checkpoint --state state/full.sqlite --out grading/checkpoint_before.json
```

It prints how many reviews were completed before the interruption.

## 4. Resume (phase "resume")

```sh
caffeinate -i uv run python -u -m pipeline.enrich --input data/raw/spotify_reviews_18months.csv --db state/full.sqlite --run-id full-resume --phase resume --workers 16 --budget-usd 30
```

The first line shows `already done N`, which matches the checkpoint. Only pending reviews are sent, so nothing is paid twice.

## 5. Snapshot again after new work (checkpoint after)

After about 1 minute, open a **second Terminal tab** (`Cmd + T`) and run:

```sh
cd ~/MBAClaude/FundamentalsAI/spotify-review-pipeline
uv run python -m pipeline checkpoint --state state/full.sqlite --out grading/checkpoint_after.json
```

The number should be larger than in step 3.

## 6. Stop the recording, but leave the run going

Stop the recording with the stop button in the menu bar and save the video. **Leave the first tab running** until it finishes, about 2–3 hours. `caffeinate -i` keeps the Mac awake while the run is going, but keep it plugged in with the lid open.
