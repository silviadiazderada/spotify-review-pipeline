"""Planted-error test: does the independent verification stage catch deliberately wrong labels?

Works on a SEPARATE TEST COPY of a development state database; business results are untouched.
The verifier never sees enrichment labels, so planting errors cannot influence its answers.

    uv run python evals/planted_error_test.py --source state/dev500.sqlite --n 10
"""

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from pipeline import config as C
from pipeline import llm, verify
from pipeline.common import connect

OUT = Path("evals/planted_error")
WRONG_TOPIC = {"playback": "billing", "billing": "access", "usability": "support", "access": "catalog",
               "catalog": "downloads", "downloads": "access", "support": "playback", "other": "billing"}
NEAR_TOPIC = {"playback": "downloads", "downloads": "playback", "billing": "usability", "usability": "billing",
              "catalog": "other", "other": "catalog", "access": "support", "support": "access"}
WRONG_INTENT = {"complaint": "praise", "cancellation": "praise", "praise": "complaint", "request": "cancellation",
                "unclear": "praise"}


def main(source, n, budget, mode):
    out = OUT / mode
    out.mkdir(parents=True, exist_ok=True)
    test_db = Path("state/test_planted.sqlite")
    for suffix in ("", "-wal", "-shm"):
        Path(f"{test_db}{suffix}").unlink(missing_ok=True)
    src = sqlite3.connect(source)
    src.execute("PRAGMA wal_checkpoint(FULL)")
    src.close()
    shutil.copy(source, test_db)
    con = connect(test_db)

    chosen, _ = verify.sample(con)
    # Plant errors in n sampled records (deterministic choice), flipping intent, topic and severity.
    targets = sorted(chosen, key=lambda r: hashlib.sha256(f"planted:{r['review_id']}".encode()).hexdigest())[:n]
    planted = []
    with con:
        for r in targets:
            if mode == "gross":   # flip intent, topic and severity
                wrong = {"intent": WRONG_INTENT[r["intent"]], "topic": WRONG_TOPIC[r["topic"]],
                         "severity": 5 if r["severity"] <= 2 else 1}
            else:                 # subtle: only the topic moves to a neighbouring category
                wrong = {"intent": r["intent"], "topic": NEAR_TOPIC[r["topic"]], "severity": r["severity"]}
            con.execute("UPDATE records SET intent=?, topic=?, severity=? WHERE review_id=?",
                        (wrong["intent"], wrong["topic"], wrong["severity"], r["review_id"]))
            planted.append({"review_id": r["review_id"], "text": r["review_text"][:120],
                            "original": {"intent": r["intent"], "topic": r["topic"], "severity": r["severity"]},
                            "planted": wrong})

    client = llm.make_client()
    report = verify.run(con, client, f"test-planted-{mode}", "initial", budget, out)
    flagged = {}
    import csv
    with (out / "verify_comparisons.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            flagged[row["review_id"]] = row
    results = []
    for p in planted:
        row = flagged[p["review_id"]]
        fields = {f: row[f"{f}_agree"] == "False" for f in ("intent", "topic", "severity")}
        results.append({**p, "verifier": {f: row[f"verify_{f}"] for f in ("intent", "topic", "severity")},
                        "disagreement_flagged": fields, "detected": any(fields.values())})
    detected = sum(r["detected"] for r in results)
    summary = {"synthetic_test": True, "mode": mode, "test_copy": str(test_db), "source": source, "planted": n,
               "detected": detected, "detection_rate": detected / n,
               "fields_flagged": {f: sum(r["disagreement_flagged"][f] for r in results) for f in ("intent", "topic", "severity")},
               "new_model_calls": report["new_model_calls"], "cases": results}
    (out / "planted_error_results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[{mode}] Planted {n} wrong labels in a test copy; verifier comparison flagged {detected}/{n} "
          f"(fields: {summary['fields_flagged']}); new model calls: {report['new_model_calls']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="state/dev500.sqlite")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--budget-usd", type=float, default=0.05)
    ap.add_argument("--mode", choices=["gross", "subtle"], default="gross")
    a = ap.parse_args()
    main(a.source, a.n, a.budget_usd, a.mode)
