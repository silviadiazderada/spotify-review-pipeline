"""Compare model predictions with the hand-labeled golden 50 (no model calls).

    uv run python evals/evaluate_golden.py --state state/golden.sqlite --out evals/golden_eval

Human labels (evals/golden_50_human.csv) are read only here, after prediction; they are never model inputs.
Sentiment tolerance is predeclared: a prediction within 0.5 of the human value counts as agreeing.
"""

import argparse
import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

HUMAN = Path("evals/golden_50_human.csv")
SENTIMENT_TOLERANCE = 0.5
TOPICS = ["access", "usability", "playback", "downloads", "catalog", "billing", "support", "other"]
INTENTS = ["cancellation", "complaint", "request", "praise", "unclear"]


def macro_f1(pairs, labels):
    f1s = []
    for lab in labels:
        tp = sum(1 for h, p in pairs if h == lab and p == lab)
        fp = sum(1 for h, p in pairs if h != lab and p == lab)
        fn = sum(1 for h, p in pairs if h == lab and p != lab)
        if tp + fp + fn == 0:
            continue  # label absent from both sides
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return round(sum(f1s) / len(f1s), 4) if f1s else None


def confusion(pairs, labels):
    m = defaultdict(Counter)
    for h, p in pairs:
        m[h][p] += 1
    rows = [lab for lab in labels if m[lab] or any(m[x][lab] for x in labels)]
    lines = ["| human \\ model | " + " | ".join(rows) + " |", "|---" * (len(rows) + 1) + "|"]
    for h in rows:
        lines.append(f"| **{h}** | " + " | ".join(str(m[h][p] or "") for p in rows) + " |")
    return "\n".join(lines)


def main(state, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(state)
    con.row_factory = sqlite3.Row
    pred = {r["review_id"]: r for r in con.execute("SELECT * FROM records")}
    with HUMAN.open(encoding="utf-8") as f:
        human = list(csv.DictReader(f))

    rows = []
    for h in human:
        p = pred.get(h["review_id"])
        row = {"review_id": h["review_id"], "review_text": h["review_text"],
               "human_intent": h["intent"], "human_topic": h["topic"], "human_severity": int(h["severity"]),
               "human_sentiment": float(h["sentiment"]), "human_needs_review": h["needs_review"] == "true",
               "human_notes": h.get("human_notes", "")}
        if p is None or p["status"] != "completed":
            row["status"] = "missing_or_quarantined"  # counts as incorrect
            rows.append(row)
            continue
        row.update({"status": "predicted", "model_intent": p["intent"], "model_topic": p["topic"],
                    "model_severity": p["severity"], "model_sentiment": p["sentiment"],
                    "model_needs_review": bool(p["needs_review"]), "model_quote": p["evidence_quote"],
                    "quote_is_exact_substring": p["evidence_quote"] in h["review_text"],
                    "quote_fallback_used": bool(p["quote_fallback"]),
                    "model_entities": p["entities"]})
        row["intent_agree"] = row["model_intent"] == row["human_intent"]
        row["topic_agree"] = row["model_topic"] == row["human_topic"]
        row["severity_agree"] = row["model_severity"] == row["human_severity"]
        row["severity_abs_err"] = abs(row["model_severity"] - row["human_severity"])
        row["sentiment_abs_err"] = abs(row["model_sentiment"] - row["human_sentiment"])
        row["sentiment_within_tol"] = row["sentiment_abs_err"] <= SENTIMENT_TOLERANCE
        rows.append(row)

    n = len(rows)
    ok = [r for r in rows if r["status"] == "predicted"]
    agree = lambda k: round(sum(r.get(k, False) for r in rows) / n, 4)  # missing counts as wrong
    nr_pairs = [(r["human_needs_review"], r["model_needs_review"]) for r in ok]
    tp = sum(h and p for h, p in nr_pairs)
    summary = {
        "n_golden": n, "predicted": len(ok), "missing_or_quarantined": n - len(ok),
        "intent_agreement": agree("intent_agree"), "topic_agreement": agree("topic_agree"),
        "intent_macro_f1": macro_f1([(r["human_intent"], r["model_intent"]) for r in ok], INTENTS),
        "topic_macro_f1": macro_f1([(r["human_topic"], r["model_topic"]) for r in ok], TOPICS),
        "severity_exact_agreement": agree("severity_agree"),
        "severity_mae": round(sum(r["severity_abs_err"] for r in ok) / len(ok), 4),
        "sentiment_mae": round(sum(r["sentiment_abs_err"] for r in ok) / len(ok), 4),
        "sentiment_within_tolerance": agree("sentiment_within_tol"),
        "sentiment_tolerance": SENTIMENT_TOLERANCE,
        "evidence_quote_exact_substring": sum(r["quote_is_exact_substring"] for r in ok),
        "evidence_quote_fallbacks": sum(r["quote_fallback_used"] for r in ok),
        "needs_review": {"human_flagged": sum(h for h, _ in nr_pairs), "model_flagged": sum(p for _, p in nr_pairs),
                         "both": tp},
        "ambiguous_cases_human_flagged": sum(r["human_needs_review"] for r in rows),
        "per_topic_counts": {"human": dict(Counter(r["human_topic"] for r in rows)),
                             "model": dict(Counter(r["model_topic"] for r in ok))},
        "per_intent_counts": {"human": dict(Counter(r["human_intent"] for r in rows)),
                              "model": dict(Counter(r["model_intent"] for r in ok))},
    }
    # Secondary, disclosed: rule-adjusted reference (adjudicated AFTER predictions were seen).
    adj_path = Path("evals/golden_rule_adjustments.csv")
    if adj_path.exists():
        adj = defaultdict(dict)
        with adj_path.open(encoding="utf-8") as f:
            for a in csv.DictReader(f):
                adj[a["review_id"]][a["field"]] = a["rule_adjusted"]
        def adj_agree(field, cast=str):
            hits = 0
            for r in ok:
                ref = adj.get(r["review_id"], {}).get(field, r[f"human_{field}"])
                hits += cast(ref) == r[f"model_{field}"]
            return round(hits / n, 4)
        summary["rule_adjusted_secondary"] = {
            "note": "Reference labels for cases where the original human label contradicted the written contract "
                    "were replaced by the rule-determined value, after model predictions were seen. Disclosed; "
                    "the primary metrics above use the original frozen labels.",
            "cases_adjusted": len(adj), "intent_agreement": adj_agree("intent"),
            "topic_agreement": adj_agree("topic"), "severity_exact_agreement": adj_agree("severity", int)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    cols = ["review_id", "status", "intent_agree", "topic_agree", "severity_agree", "sentiment_within_tol",
            "human_intent", "model_intent", "human_topic", "model_topic", "human_severity", "model_severity",
            "human_sentiment", "model_sentiment", "human_needs_review", "model_needs_review",
            "quote_is_exact_substring", "quote_fallback_used", "model_quote", "model_entities", "human_notes",
            "review_text"]
    with (out / "per_case.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    md = [f"# Golden-50 evaluation\n",
          f"Predictions: `{state}` (label_config `{ok[0]['review_id'] and pred[ok[0]['review_id']]['label_config']}`). "
          f"Human labels: `{HUMAN}`. Missing or quarantined predictions count as incorrect.\n",
          "| Field | Result |", "|---|---|"]
    md += [f"| Intent agreement | {summary['intent_agreement']:.0%} (macro F1 {summary['intent_macro_f1']}) |",
           f"| Topic agreement | {summary['topic_agreement']:.0%} (macro F1 {summary['topic_macro_f1']}) |",
           f"| Severity exact agreement | {summary['severity_exact_agreement']:.0%} (MAE {summary['severity_mae']}) |",
           f"| Sentiment within ±{SENTIMENT_TOLERANCE} | {summary['sentiment_within_tolerance']:.0%} "
           f"(MAE {summary['sentiment_mae']}) |",
           f"| Evidence quote exact substring | {summary['evidence_quote_exact_substring']}/{len(ok)} "
           f"({summary['evidence_quote_fallbacks']} replaced by full text in code) |",
           f"| needs_review | human {summary['needs_review']['human_flagged']}, model "
           f"{summary['needs_review']['model_flagged']}, both {summary['needs_review']['both']} |",
           *([f"\n**Secondary, rule-adjusted reference (disclosed, adjudicated after predictions were seen; "
              f"{summary['rule_adjusted_secondary']['cases_adjusted']} cases, see `evals/golden_rule_adjustments.csv`):** "
              f"intent {summary['rule_adjusted_secondary']['intent_agreement']:.0%}, "
              f"topic {summary['rule_adjusted_secondary']['topic_agreement']:.0%}, "
              f"severity {summary['rule_adjusted_secondary']['severity_exact_agreement']:.0%}. "
              f"Primary results above use the original frozen human labels."] if "rule_adjusted_secondary" in summary else []),
           "\n## Intent confusion\n", confusion([(r["human_intent"], r["model_intent"]) for r in ok], INTENTS),
           "\n## Topic confusion\n", confusion([(r["human_topic"], r["model_topic"]) for r in ok], TOPICS),
           "\n## Disagreements\n", "| # | Text (first 100 chars) | Human (intent/topic/sev) | Model | Human note |",
           "|---|---|---|---|---|"]
    for i, r in enumerate(rows, start=1):
        if r["status"] != "predicted" or not (r["intent_agree"] and r["topic_agree"] and r["severity_agree"]):
            t = r["review_text"][:100].replace("|", "/").replace("\n", " ")
            m = (f"{r.get('model_intent')}/{r.get('model_topic')}/{r.get('model_severity')}"
                 if r["status"] == "predicted" else "missing")
            md.append(f"| {i} | {t} | {r['human_intent']}/{r['human_topic']}/{r['human_severity']} | {m} | "
                      f"{r['human_notes']} |")
    (out / "report.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="state/golden.sqlite")
    ap.add_argument("--out", default="evals/golden_eval")
    a = ap.parse_args()
    main(a.state, a.out)
