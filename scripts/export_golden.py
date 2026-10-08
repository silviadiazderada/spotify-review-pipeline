"""Export the hand-labeled golden spreadsheet to the course CSV format. No AI involved.

Usage:
    uv run python scripts/export_golden.py
"""

import csv
import hashlib
from pathlib import Path

import openpyxl

SRC_CSV = Path("data/raw/golden_50_to_label.csv")
SHEET = Path("evals/golden_50_labeling.xlsx")
OUT = Path("evals/golden_50_human.csv")
LABELS = ["topic", "intent", "sentiment", "severity", "entities", "evidence_quote", "needs_review"]


def main():
    ws = openpyxl.load_workbook(SHEET)["Label here"]
    header = [c.value for c in ws[1]]
    header[0] = "#"  # column A header was overwritten by accident during labeling
    human = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        r = dict(zip(header, row))
        if r.get("review_id"):
            human[r["review_id"]] = r

    with SRC_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames + ["human_notes"]
        source = list(reader)

    missing = [s["review_id"] for s in source if s["review_id"] not in human]
    assert not missing and len(human) == 50, f"ID mismatch: {missing}"

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in source:  # source values are copied unchanged; only label columns are filled
            h = human[s["review_id"]]
            s.update({
                "topic": h["topic"], "intent": h["intent"],
                "sentiment": str(float(h["sentiment"])), "severity": str(int(h["severity"])),
                "entities": "", "evidence_quote": h.get("evidence_quote") or "",
                "needs_review": str(h["needs_review"] == "yes").lower(),
                "human_notes": h.get("notes") or "",
            })
            w.writerow(s)

    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"Saved {OUT} (50 rows), sha256 {digest}")


if __name__ == "__main__":
    main()
