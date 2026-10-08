"""Stage 1 - Prepare (no AI, no API key, no cost).

Reads every row of the input CSV, keeps IDs and source values exactly as they are,
profiles data quality, finds exact duplicate texts, quarantines empty texts and
writes the queue of distinct texts that the AI stage will need to classify.

Usage:
    uv run python scripts/01_prepare.py data/raw/spotify_reviews_18months.csv
"""

import csv
import hashlib
import json
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Same field order and serialization as the course checker (check_submission.py).
FIELDS = ("review_id", "review_text", "review_rating", "review_likes", "app_version", "review_timestamp")

# Numbers stated in the assignment brief and manifest.json, used as a cross-check.
EXPECTED_FULL = {
    "records": 660622,
    "duplicate_review_ids": 0,
    "empty_review_text": 13,
    "missing_app_version": 159701,
    "distinct_nonempty_texts": 484189,
}

OUT_DIR = Path("data/prepared")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def row_sha(row):
    # Exact source strings: no trimming, translating or Unicode normalization.
    return hashlib.sha256(canonical([row[k] for k in FIELDS]).encode("utf-8")).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, strict=True)
        missing = [k for k in FIELDS if k not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Input CSV is missing columns: {missing}")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Malformed CSV row")
            yield row


def main(input_path):
    started = time.time()
    input_path = Path(input_path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Reading {input_path} ...")

    counts = Counter(records=0, duplicate_review_ids=0, empty_review_text=0, missing_app_version=0)
    months, ratings = Counter(), Counter()
    seen_ids = set()
    first_ts = last_ts = None
    content = hashlib.sha256()

    # text hash -> [first review_id with that exact text, number of copies, text]
    distinct = {}
    lengths = []

    records_path = OUT_DIR / "records_prepared.csv"
    with records_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["review_id", "source_sha256", "status", "reason", "text_sha256", "cache_source_id"])

        for row in csv_rows(input_path):
            rid = row["review_id"]
            digest = row_sha(row)
            content.update(bytes.fromhex(digest))

            counts["records"] += 1
            counts["duplicate_review_ids"] += rid in seen_ids
            seen_ids.add(rid)
            counts["missing_app_version"] += not row["app_version"].strip()
            months[row["review_timestamp"][:7]] += 1
            ratings[row["review_rating"]] += 1
            ts = row["review_timestamp"]
            first_ts = min(first_ts, ts) if first_ts else ts
            last_ts = max(last_ts, ts) if last_ts else ts

            text = row["review_text"]
            if not text.strip():
                counts["empty_review_text"] += 1
                writer.writerow([rid, digest, "quarantined", "empty_review_text", "", ""])
                continue

            # Exact-text reuse: identical text (byte for byte) shares one future AI result.
            th = text_sha(text)
            if th in distinct:
                distinct[th][1] += 1
                cache_source = distinct[th][0]
            else:
                distinct[th] = [rid, 1, text]
                lengths.append(len(text))
                cache_source = ""
            writer.writerow([rid, digest, "pending", "", th, cache_source])

    # Queue of distinct texts: this is the only work the paid AI stage needs to do.
    queue_path = OUT_DIR / "pending_texts.csv"
    with queue_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["text_sha256", "first_review_id", "copies", "review_text"])
        for th, (rid, copies, text) in distinct.items():
            writer.writerow([th, rid, copies, text])

    nonempty = counts["records"] - counts["empty_review_text"]
    top_dupes = sorted(distinct.values(), key=lambda v: -v[1])[:15]
    total_chars = sum(lengths)

    observed = dict(counts, distinct_nonempty_texts=len(distinct))
    checks = {}
    if counts["records"] == EXPECTED_FULL["records"]:
        checks = {k: {"expected": v, "observed": observed[k], "match": observed[k] == v} for k, v in EXPECTED_FULL.items()}

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_file": input_path.name,
        "file_bytes": input_path.stat().st_size,
        "file_sha256": file_sha(input_path),
        "parsed_rows_sha256": content.hexdigest(),
        "counts": dict(counts),
        "nonempty_to_classify": nonempty,
        "quarantined_empty_text": counts["empty_review_text"],
        "distinct_nonempty_texts": len(distinct),
        "duplicate_rows_reusing_a_result": nonempty - len(distinct),
        "checks_against_brief": checks,
        "first_review": first_ts,
        "last_review": last_ts,
        "reviews_by_month": dict(sorted(months.items())),
        "reviews_by_rating": dict(sorted(ratings.items())),
        "distinct_text_length_chars": {
            "total": total_chars,
            "mean": round(total_chars / len(lengths), 1) if lengths else 0,
            "median": statistics.median(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "approx_tokens_total": total_chars // 4,
        },
        "most_repeated_texts": [{"text": t[:80], "copies": c, "first_review_id": r} for r, c, t in top_dupes],
        "outputs": [str(records_path), str(queue_path)],
        "runtime_seconds": round(time.time() - started, 1),
    }
    (OUT_DIR / "ingestion_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print()
    print(f"Rows read:                 {counts['records']:,}")
    print(f"Repeated review IDs:       {counts['duplicate_review_ids']:,}")
    print(f"Empty texts (quarantined): {counts['empty_review_text']:,}")
    print(f"Missing app version:       {counts['missing_app_version']:,}")
    print(f"Non-empty to classify:     {nonempty:,}")
    print(f"Distinct texts (AI work):  {len(distinct):,}  ({nonempty - len(distinct):,} rows reuse a result)")
    print(f"Dates:                     {first_ts} -> {last_ts}")
    if checks:
        ok = all(c["match"] for c in checks.values())
        print(f"Matches assignment numbers: {'YES' if ok else 'NO - see report'}")
    print(f"\nReport: {OUT_DIR / 'ingestion_report.json'}  ({report['runtime_seconds']}s)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: uv run python scripts/01_prepare.py <input.csv>")
    main(sys.argv[1])
