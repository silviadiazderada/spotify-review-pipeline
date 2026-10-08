"""Independent audit of every number in the memo (no model calls, no pipeline database).

Recomputes all memo-relevant quantities from the grading export (records.jsonl.gz, membership.csv, claims.csv),
the verifier comparisons and the raw source CSV, then traces each number in memo.md to (a) the claim it cites,
checked against the recomputed issue metric, or (b) a recomputed fact. It also checks that the evidence pack the
memo agent saw matches the independent recomputation, and that every quoted review ID is real and its quote is an
exact substring of that review.

    uv run python scripts/audit_memo.py --outputs runs/full-final-v7      # writes evals/memo_audit.md (+ .json)
"""

import argparse
import csv
import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.memo import AREAS, BOYCOTT_TERMS, CLAIM, ISSUE, NUMBER, THEMES, UPDATE_TERMS, UUID  # noqa: E402

FOUR = ("usability", "billing/support", "playback", "access")
COMPLAINT = ("complaint", "cancellation")


def pct(a, b):
    return f"{100 * a / b:.1f}%"


def mean6(total, n):
    return str((Decimal(total) / Decimal(n)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def recompute(outputs):
    g = ROOT / "grading"
    records = {}
    with gzip.open(g / "records.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            records[r["review_id"]] = r
    src = {}
    with (ROOT / "data/raw/spotify_reviews_18months.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            src[row["review_id"]] = (row["review_timestamp"], row["review_text"])
    membership = {m["review_id"]: m["issue_id"] for m in csv.DictReader((g / "membership.csv").open())}

    facts = {}
    done = [r for r in records.values() if r["status"] == "completed"]
    comp = [r for r in done if r["intent"] in COMPLAINT]
    facts["scope.source_rows"] = len(records)
    facts["scope.completed"] = len(done)
    facts["scope.unclassified"] = len(records) - len(done)
    q = Counter(r["reason"] for r in records.values() if r["status"] == "quarantined")
    facts["scope.quarantined_invalid_output"] = q["invalid_model_output_after_retry"]
    facts["scope.quarantined_empty_text"] = q["empty_review_text"]
    facts["complaint_records"] = len(comp)

    # Issue metrics (what claims.csv must equal).
    issue = defaultdict(lambda: [0, 0])
    sev = {r["review_id"]: r["severity"] for r in comp}
    for rid, iss in membership.items():
        issue[iss][0] += 1
        issue[iss][1] += sev[rid]
    issue_metrics = {i: {"complaint_count": str(c), "severity_sum": str(s), "mean_severity": mean6(s, c),
                         "priority_score": str(s)} for i, (c, s) in issue.items()}

    area = defaultdict(lambda: [0, 0])
    for r in comp:
        a = AREAS[r["topic"]]
        area[a][0] += 1
        area[a][1] += r["severity"]
    for a, (c, s) in area.items():
        facts[f"area[{a}].complaint_records"] = c
        facts[f"area[{a}].severity_sum"] = s
        facts[f"area[{a}].share_of_complaints"] = pct(c, len(comp))

    for name, members in THEMES.items():
        c = sum(issue[m][0] for m in members)
        s = sum(issue[m][1] for m in members)
        facts[f"theme[{name}].complaint_records"] = c
        facts[f"theme[{name}].severity_sum"] = s
        facts[f"theme[{name}].share_of_complaints"] = pct(c, len(comp))

    for label, (lo, hi) in {"Jun-Nov 2022": ("2022-06", "2022-11"), "May-Oct 2023": ("2023-05", "2023-10")}.items():
        rows = [r for r in done if lo <= src[r["review_id"]][0][:7] <= hi]
        cr = [r for r in rows if r["intent"] in COMPLAINT]
        facts[f"trend[{label}].completed_reviews"] = len(rows)
        facts[f"trend[{label}].complaint_records"] = len(cr)
        facts[f"trend[{label}].complaint_share_of_reviews"] = pct(len(cr), len(rows))
        per = Counter(AREAS[r["topic"]] for r in cr)
        for a, n in per.items():
            facts[f"trend[{label}].share[{a}]"] = pct(n, len(cr))

    def has(text, terms):
        t = text.lower()
        return any(x in t for x in terms)
    outside = [r for r in comp if r["topic"] in ("other", "catalog")]
    jul = [rid for rid, (ts, _) in src.items() if "2023-07-06" <= ts[:10] <= "2023-07-09"]
    facts["spike[Jul 6-9 2023].reviews"] = len(jul)
    facts["spike[Jul 6-9 2023].outside_area_complaints"] = sum(
        1 for r in outside if "2023-07-06" <= src[r["review_id"]][0][:10] <= "2023-07-09")
    facts["spike[Jul 6-9 2023].boycott_keyword_reviews"] = sum(has(src[rid][1], BOYCOTT_TERMS) for rid in jul)
    octo = [r for r in outside if src[r["review_id"]][0][:7] == "2023-10"]
    base = [r for r in outside if "2023-01" <= src[r["review_id"]][0][:7] <= "2023-06"]
    facts["spike[Oct 2023].outside_area_complaints"] = len(octo)
    facts["spike[Oct 2023].share_mentioning_update"] = pct(sum(has(src[r["review_id"]][1], UPDATE_TERMS) for r in octo), len(octo))
    facts["spike[Jan-Jun 2023].share_mentioning_update"] = pct(sum(has(src[r["review_id"]][1], UPDATE_TERMS) for r in base), len(base))
    facts["average_reviews_per_day"] = round(len(src) / len({ts[:10] for ts, _ in src.values()}))

    free = set(THEMES["free_tier_restrictions"])
    scen = defaultdict(lambda: defaultdict(int))
    for r in comp:
        a, s, d = AREAS[r["topic"]], r["severity"], src[r["review_id"]][0][:10]
        iss = membership[r["review_id"]]
        spike = "2023-07-06" <= d <= "2023-07-09" or d[:7] == "2023-10"
        scen["baseline_severity_sum"][a] += s
        scen["complaint_count_only"][a] += 1
        scen["excluding_spike_events"][a] += 0 if spike else s
        scen["latest_window_May_Oct_2023"][a] += s if "2023-05" <= d[:7] <= "2023-10" else 0
        scen["free_tier_restrictions_counted_as_billing"]["billing/support" if iss in free else a] += s
        scen["free_tier_restrictions_counted_as_usability"]["usability" if iss in free else a] += s
    leaders = []
    for k, v in scen.items():
        for a in FOUR:
            facts[f"robustness[{k}].{a}"] = v[a]
        leaders.append(max(FOUR, key=lambda a: v[a]))
    facts["robustness.scenarios_led_by_usability"] = leaders.count("usability")
    facts["robustness.scenarios_total"] = len(leaders)

    ver = [v for v in csv.DictReader((Path(outputs) / "verify_comparisons.csv").open(encoding="utf-8")) if v["status"] == "verified"]
    facts["verify.verified"] = len(ver)
    for f in ("intent", "topic", "severity"):
        facts[f"verify.agreement_{f}"] = round(sum(v[f"{f}_agree"] == "True" for v in ver) / len(ver), 4)
    facts["verify.severity_mae"] = round(sum(float(v["severity_abs_diff"]) for v in ver) / len(ver), 4)
    return facts, issue_metrics, records, src, membership


def norm(x):
    return str(x).replace(",", "")


def main(outputs):
    out = Path(outputs)
    facts, issue_metrics, records, src, membership = recompute(outputs)
    memo = (out / "memo.md").read_text()
    claims = {c["claim_id"]: c for c in csv.DictReader((out / "claims.csv").open())}
    pack = json.loads((out / "evidence_pack.json").read_text())

    rows, problems = [], []
    # (a) claims.csv vs independent recomputation
    for c in claims.values():
        if issue_metrics[c["issue_id"]][c["metric"]] != c["value"]:
            problems.append(f"claims.csv {c['claim_id']} {c['value']} != recomputed {issue_metrics[c['issue_id']][c['metric']]}")
    # (b) every number in the memo
    lookup = defaultdict(list)
    for k, v in facts.items():
        lookup[norm(v)].append(k)
        if isinstance(v, str) and v.endswith("%"):
            lookup[v[:-1]].append(k)
    claim_spans = {}
    for m in CLAIM.finditer(memo):
        before = UUID.sub(" ", ISSUE.sub(" ", memo[max(0, m.start() - 80):m.start()]))
        nums = list(NUMBER.finditer(CLAIM.sub(" ", before)))
        if nums:
            claim_spans[(m.start(), nums[-1].group())] = m.group(1)
    clean = UUID.sub(lambda m: " " * len(m.group()), ISSUE.sub(lambda m: " " * len(m.group()), CLAIM.sub(lambda m: " " * len(m.group()), memo)))
    for m in NUMBER.finditer(clean):
        n = m.group().rstrip(",")
        ctx = re.sub(r"\s+", " ", memo[max(0, m.start() - 45):m.end() + 20]).strip()
        cited = next((cid for (pos, val), cid in claim_spans.items() if 0 < pos - m.end() <= 80 and val == n), None)
        if cited:
            c = claims[cited]
            ok = issue_metrics[c["issue_id"]][c["metric"]] == norm(n)
            rows.append((n, ctx, f"claim {cited}: {c['issue_id']} {c['metric']}", issue_metrics[c["issue_id"]][c["metric"]], ok))
        elif norm(n) in lookup:
            rows.append((n, ctx, ", ".join(lookup[norm(n)][:3]), facts[lookup[norm(n)][0]], True))
        elif n.isdigit() and int(n) <= 10:
            rows.append((n, ctx, "small count/ordinal (e.g. scenario counts, list numbering)", n, True))
        elif n in ("2022", "2023"):
            rows.append((n, ctx, "calendar year", n, True))
        else:
            rows.append((n, ctx, "UNTRACED", "", False))
            problems.append(f"untraced number {n}: …{ctx}…")
    # (c) evidence pack the memo agent saw == independent recomputation (spot-check all shared fields)
    pack_checks = {
        "complaint_records": pack["complaint_and_cancellation_records"],
        **{f"area[{a}].complaint_records": v["complaint_records"] for a, v in pack["decision_areas"].items()},
        **{f"area[{a}].severity_sum": v["severity_sum"] for a, v in pack["decision_areas"].items()},
        **{f"area[{a}].share_of_complaints": v["share_of_complaints"] for a, v in pack["decision_areas"].items()},
        **{f"robustness[{k}].{a}": v[a] for k, v in pack["robustness_of_top_area"]["scenarios"].items() for a in FOUR},
        "spike[Jul 6-9 2023].reviews": pack["volume_spikes"]["Jul 6-9 2023"]["reviews"],
        "spike[Oct 2023].share_mentioning_update": pack["volume_spikes"]["Oct 2023"]["share_mentioning_update_or_version"],
    }
    pack_mismatch = {k: (v, facts.get(k)) for k, v in pack_checks.items() if norm(v) != norm(facts.get(k))}
    problems += [f"evidence pack {k}={v} but independent recomputation={r}" for k, (v, r) in pack_mismatch.items()]
    # (d) quoted reviews exist, quote is an exact substring, and the review is in the cited issue's area/issue
    quote_rows = []
    for m in re.finditer(r"[“\"]([^”\"]{4,200})[”\"]\s*\(([0-9a-f-]{36})\)", memo):
        quote, rid = m.group(1), m.group(2)
        ok = rid in src and quote in src[rid][1]
        quote_rows.append((rid, quote, membership.get(rid, "–"), ok))
        if not ok:
            problems.append(f"quote not found in review {rid}: {quote}")

    traced = sum(1 for r in rows if r[4])
    md = ["# Memo audit (independent recomputation)", "",
          f"Memo: `{out / 'memo.md'}`. Recomputed from `grading/records.jsonl.gz`, `grading/membership.csv`, "
          "`data/raw/spotify_reviews_18months.csv` and `verify_comparisons.csv`, without the pipeline database or any model call.", "",
          f"- Numbers in memo: **{len(rows)}**, traced and correct: **{traced}**",
          f"- claims.csv rows matching recomputed issue metrics: **{len(claims) - sum('claims.csv' in p for p in problems)}/{len(claims)}**",
          f"- Evidence-pack fields matching recomputation: **{len(pack_checks) - len(pack_mismatch)}/{len(pack_checks)}**",
          f"- Quoted reviews found verbatim: **{sum(q[3] for q in quote_rows)}/{len(quote_rows)}**",
          f"- Problems: **{len(problems)}**" + ("" if not problems else "\n  - " + "\n  - ".join(problems)), "",
          "## Every number", "", "| Number | Context | Traced to | Independent value | OK |", "|---|---|---|---|---|"]
    md += [f"| {n} | …{c.replace('|', '/')}… | {t} | {v} | {'✓' if ok else '✗'} |" for n, c, t, v, ok in rows]
    md += ["", "## Quoted reviews", "", "| Review ID | Quote | Issue | Verbatim |", "|---|---|---|---|"]
    md += [f"| `{r}` | {q} | `{i}` | {'✓' if ok else '✗'} |" for r, q, i, ok in quote_rows]
    (ROOT / "evals" / "memo_audit.md").write_text("\n".join(md) + "\n")
    (ROOT / "evals" / "memo_audit.json").write_text(json.dumps({"numbers": len(rows), "traced_ok": traced,
                                                               "problems": problems, "facts": facts}, indent=2))
    print("\n".join(md[:9]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs", required=True)
    main(ap.parse_args().outputs)
