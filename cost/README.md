# Cost and runtime calculator (100-review pilot)

## Offline replay (default, free)

No API key, no network, no model calls. Uses the Python standard library only.

```sh
python3 cost/calculator.py                        # recompute everything and write cost/report.md
python3 cost/calculator.py --rates-multiplier 2   # sensitivity check: API spend doubles, measured time does not
```

Edit `cost/rates.csv` (prices) or `cost/assumptions.json` (budget, workers, output cap, fallback fraction, retry, prompt-cache and projection assumptions), then rerun. Changing projection inputs never changes the recorded pilot measurements.

## Explicit paid pilot (separate command)

This command spends money. It requires `.env` with `OPENAI_API_KEY` and an empty `state/pilot.sqlite`.

```sh
uv run python cost/calculator.py pilot --confirm-paid --budget-usd 0.50
```

It runs the whole pipeline on `data/raw/cost_100.csv` with 1 worker:

1. A **cold** run (`pilot-cold`), starting from an empty result cache.
2. A **warm** run (`pilot-warm`), with saved results.

It then collects the evidence (`cost/collect.py`) and regenerates the report.

## Files

| File | Contents |
|---|---|
| `report.md` | Measured cold/warm table, per-stage usage and cost, full-run base/conservative scenarios with and without exact-text reuse, budget check |
| `pilot_records.jsonl` | One final record per pilot ID: grading-contract format, original row hash, common labels |
| `pilot_calls.jsonl` | Every attempted call (cold and warm): role, model, effort, prompt/label config, reviews sent, outcome, usage, provider request ID, timing |
| `pilot_runs.json` | Run-level measurements: wall-clock, stage times, record status, cache hits, input checksum |
| `usage.csv` | Every billed item mapped to its request ID and billed units |
| `rates.csv` | Editable prices with units, tier, dated source links |
| `assumptions.json` | Editable controls and projection assumptions |
