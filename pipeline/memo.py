"""Stage 6 - Recommend. Code builds claims.csv and a bounded evidence pack from saved aggregates;
the memo model writes from that pack only; code then checks every cited claim ID, review ID,
issue ID and number. One corrective retry is allowed, then the result is saved with its check."""

import csv
import json
import re
from collections import Counter
from pathlib import Path

from pipeline import config as C
from pipeline import llm

PROMPT = (C.PROMPTS / f"{C.MEMO_PROMPT_VERSION}.txt").read_text()
MEMO_CONFIG = f"{C.MEMO_MODEL}+effort-{C.MEMO_EFFORT}+{C.MEMO_PROMPT_VERSION}"
METRICS = ("complaint_count", "severity_sum", "mean_severity", "priority_score")

# The assignment's four decision areas. catalog and other fall outside them and are reported separately.
AREAS = {"access": "access", "usability": "usability", "playback": "playback", "downloads": "playback",
         "billing": "billing/support", "support": "billing/support", "catalog": "outside the four areas",
         "other": "outside the four areas"}

# Cross-area themes (code-defined, documented): the shared taxonomy splits free-tier restrictions between
# billing (Premium-locked controls, paywalls) and usability (shuffle/skip limits, ads).
THEMES = {
    "free_tier_experience_ads_plus_restrictions": ["ISS-usability-ads", "ISS-billing-premium_only_controls",
                                                  "ISS-billing-basic_features_paywalled",
                                                  "ISS-usability-shuffle_skip_limits"],
    "free_tier_restrictions": ["ISS-billing-premium_only_controls", "ISS-billing-basic_features_paywalled",
                               "ISS-usability-shuffle_skip_limits"],
    "ads": ["ISS-usability-ads"],
}
# Comparable 6-month periods; the first (May 2022) and last (Nov 2023) months are partial and excluded.
PERIODS = {"Jun-Nov 2022": ("2022-06", "2022-11"), "May-Oct 2023": ("2023-05", "2023-10")}

# Volume spikes found in exploratory analysis (code-defined windows; numbers are recomputed from the data).
BOYCOTT_TERMS = ("sweden", "swedish", "quran", "koran", "boycott", "islam", "muslim")
UPDATE_TERMS = ("update", "version", "new ui", "new design")


def spike_events(con):
    def kw(col_terms):
        return " OR ".join(f"lower(review_text) LIKE '%{t}%'" for t in col_terms)
    outside = "status='completed' AND intent IN ('complaint','cancellation') AND topic IN ('other','catalog')"
    days = con.execute("SELECT COUNT(DISTINCT substr(review_timestamp,1,10)) FROM records").fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    jul = con.execute(f"SELECT COUNT(*), SUM({kw(BOYCOTT_TERMS)}) FROM records WHERE substr(review_timestamp,1,10)"
                      " BETWEEN '2023-07-06' AND '2023-07-09'").fetchone()
    jul_out = con.execute(f"SELECT COUNT(*) FROM records WHERE {outside} AND substr(review_timestamp,1,10)"
                          " BETWEEN '2023-07-06' AND '2023-07-09'").fetchone()[0]
    octo = con.execute(f"SELECT COUNT(*), SUM({kw(UPDATE_TERMS)}) FROM records WHERE {outside}"
                       " AND substr(review_timestamp,1,7)='2023-10'").fetchone()
    base = con.execute(f"SELECT COUNT(*), SUM({kw(UPDATE_TERMS)}) FROM records WHERE {outside}"
                       " AND substr(review_timestamp,1,7) BETWEEN '2023-01' AND '2023-06'").fetchone()
    return {
        "note": "Outside-area complaints are concentrated in two events. Keyword matches are a lower bound "
                "(many reviews are one-line insults without a stated reason); the external cause is not in the data.",
        "average_reviews_per_day_whole_period": round(total / days),
        "Jul 6-9 2023": {"reviews": jul[0], "outside_area_complaints": jul_out,
                         "reviews_mentioning_sweden_quran_islam_or_boycott": jul[1],
                         "reading": "short coordinated one-line complaints (review bombing) consistent with a boycott campaign"},
        "Oct 2023": {"outside_area_complaints": octo[0],
                     "share_mentioning_update_or_version": pct(octo[1], octo[0]),
                     "same_share_Jan_Jun_2023": pct(base[1], base[0]),
                     "reading": "backlash against an app update without a specific defect named"},
    }


FOUR_AREAS = ("usability", "billing/support", "playback", "access")


def robustness(con, membership):
    """Does the top decision area survive reasonable alternative ranking choices? (code-computed scenarios)"""
    free = set(THEMES["free_tier_restrictions"])
    scen = {k: {a: 0 for a in FOUR_AREAS} for k in (
        "baseline_severity_sum", "complaint_count_only", "excluding_spike_events", "latest_window_May_Oct_2023",
        "free_tier_restrictions_counted_as_billing", "free_tier_restrictions_counted_as_usability")}
    for rid, topic, sev, d in con.execute(
            "SELECT review_id, topic, severity, substr(review_timestamp,1,10) FROM records WHERE status='completed'"
            " AND intent IN ('complaint','cancellation')"):
        a = AREAS[topic]
        iss = membership.get(rid)
        spike = "2023-07-06" <= d <= "2023-07-09" or d[:7] == "2023-10"
        for key, area, add in (
                ("baseline_severity_sum", a, sev), ("complaint_count_only", a, 1),
                ("excluding_spike_events", a, 0 if spike else sev),
                ("latest_window_May_Oct_2023", a, sev if "2023-05" <= d[:7] <= "2023-10" else 0),
                ("free_tier_restrictions_counted_as_billing", "billing/support" if iss in free else a, sev),
                ("free_tier_restrictions_counted_as_usability", "usability" if iss in free else a, sev)):
            if area in scen[key]:
                scen[key][area] += add
    out = {}
    for key, vals in scen.items():
        order = sorted(FOUR_AREAS, key=lambda x: -vals[x])
        out[key] = {"leader": order[0], "runner_up": order[1], **{a: vals[a] for a in order}}
    leaders = [v["leader"] for v in out.values()]
    return {"note": "Severity sums (or counts) over complaint/cancellation records in the four decision areas under "
                    "alternative ranking choices; 'outside the four areas' is excluded.",
            "scenarios": out,
            "scenarios_led_by_usability": leaders.count("usability"),
            "scenarios_led_by_billing_support": leaders.count("billing/support"),
            "scenarios_total": len(leaders)}


UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
CLAIM = re.compile(r"\[(C\d{3})\]")
ISSUE = re.compile(r"ISS-[a-z]+-[a-z_]+")
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def build_claims(ranking, top_n):
    claims = []
    for r in ranking[:top_n]:
        for m in METRICS:
            claims.append({"claim_id": f"C{len(claims) + 1:03d}", "issue_id": r["issue_id"], "metric": m,
                           "value": str(r[m])})
    return claims


def build_pack(con, ranking, issues, claims, verify_report, records_counts, membership=None):
    completed = con.execute("SELECT COUNT(*) FROM records WHERE status='completed'").fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    intents = Counter(r[0] for r in con.execute("SELECT intent FROM records WHERE status='completed'"))
    complaints = intents["complaint"] + intents["cancellation"]

    area = {}
    for r in con.execute("SELECT topic, severity FROM records WHERE status='completed'"
                         " AND intent IN ('complaint','cancellation')"):
        a = area.setdefault(AREAS[r[0]], {"complaint_records": 0, "severity_sum": 0})
        a["complaint_records"] += 1
        a["severity_sum"] += r[1]
    for a in area.values():
        a["share_of_complaints"] = pct(a["complaint_records"], complaints)

    claim_ids = {}
    for c in claims:
        claim_ids.setdefault(c["issue_id"], {})[c["metric"]] = c["claim_id"]
    top = []
    for r in ranking[:C.MEMO_TOP_ISSUES]:
        iss = issues[r["issue_id"]]
        quotes = []
        for rid in iss["example_review_ids"].split()[:3]:
            q = con.execute("SELECT evidence_quote, severity FROM records WHERE review_id=?", (rid,)).fetchone()
            quotes.append({"review_id": rid, "quote": q[0][:200], "severity": q[1]})
        top.append({"rank": r["rank"], "issue_id": r["issue_id"], "name": iss["name"],
                    "description": iss["description"], "decision_area": AREAS[iss["topic"]],
                    **{m: {"value": str(r[m]), "claim_id": claim_ids[r["issue_id"]][m]} for m in METRICS},
                    "evidence": quotes})
    dates = con.execute("SELECT MIN(review_timestamp), MAX(review_timestamp) FROM records").fetchone()
    by_issue = {r["issue_id"]: r for r in ranking}
    themes = {}
    for name, members in THEMES.items():
        present = [m for m in members if m in by_issue]
        cc = sum(by_issue[m]["complaint_count"] for m in present)
        themes[name] = {"issues": present, "complaint_records": cc, "severity_sum": sum(by_issue[m]["severity_sum"] for m in present),
                        "share_of_complaints": pct(cc, complaints)}
    trend = {}
    for label, (a, b) in PERIODS.items():
        rows = con.execute(
            "SELECT topic, intent FROM records WHERE status='completed' AND substr(review_timestamp,1,7) BETWEEN ? AND ?",
            (a, b)).fetchall()
        comp = [r for r in rows if r[1] in ("complaint", "cancellation")]
        per_area = Counter(AREAS[r[0]] for r in comp)
        trend[label] = {"completed_reviews": len(rows), "complaint_records": len(comp),
                        "complaint_share_of_reviews": pct(len(comp), len(rows)),
                        "area_share_of_complaints": {k: pct(v, len(comp)) for k, v in sorted(per_area.items())}}
    return {
        "scope": {"source_rows": total, "completed_classifications": completed,
                  "not_classified": total - completed, "record_status": records_counts,
                  "first_review": dates[0], "last_review": dates[1]},
        "intent_counts": dict(intents),
        "complaint_and_cancellation_records": complaints,
        "complaints_share_of_completed": pct(complaints, completed),
        "cancellation_intent_records": intents["cancellation"],
        "decision_areas": area,
        "ranking_rule": "priority_score = complaint_count x mean_severity = severity_sum; one issue per complaint",
        "issues_ranked_total": len(ranking),
        "top_issues": top,
        "verification": {k: verify_report.get(k) for k in ("sampled", "verified", "agreement", "severity_mae")},
        "cross_area_themes": {
            "note": "The shared taxonomy files Premium-locked controls and paywalls under billing but shuffle/skip limits "
                    "and ads under usability; these code-defined themes add up the related issues across areas.",
            **themes},
        "volume_spikes": spike_events(con),
        "robustness_of_top_area": robustness(con, membership or {}),
        "trend_comparable_periods": {
            "note": "Shares among completed reviews in two comparable 6-month windows; first and last calendar months "
                    "of the data are partial and excluded. Review volume is self-selected and varies by month.",
            **trend},
    }


def check(memo, pack, claims, ranking):
    problems = []
    valid_claims = {c["claim_id"] for c in claims}
    cited = set(CLAIM.findall(memo))
    if not cited:
        problems.append("no claim IDs cited")
    problems += [f"unknown claim ID {c}" for c in sorted(cited - valid_claims)]
    pack_text = json.dumps(pack, ensure_ascii=False)
    pack_ids = set(UUID.findall(pack_text))
    problems += [f"review ID not in evidence pack: {r}" for r in sorted(set(UUID.findall(memo)) - pack_ids)]
    by_id = {c["claim_id"]: c for c in claims}
    for m in re.finditer(r"\[(C\d{3})\]", memo):
        c = by_id.get(m.group(1))
        if not c:
            continue
        before = UUID.sub(" ", ISSUE.sub(" ", memo[max(0, m.start() - 80):m.start()]))
        nums = NUMBER.findall(CLAIM.sub(" ", before))
        if not nums or nums[-1].replace(",", "") != c["value"]:
            problems.append(f"{c['claim_id']} cites {c['metric']}={c['value']} but the preceding number is "
                            f"{nums[-1] if nums else 'missing'}")
    valid_issues = {r["issue_id"] for r in ranking}
    problems += [f"unknown issue ID {i}" for i in sorted(set(ISSUE.findall(memo)) - valid_issues)]
    # Numbers: strip IDs first, then every number must appear verbatim in the pack (small integers allowed).
    stripped = ISSUE.sub(" ", CLAIM.sub(" ", UUID.sub(" ", memo)))
    allowed = {n.replace(",", "") for n in NUMBER.findall(UUID.sub(" ", pack_text))} | {str(i) for i in range(11)}
    for n in NUMBER.findall(stripped):
        if n.replace(",", "") not in allowed:
            problems.append(f"number not found in evidence pack: {n}")
    return {"passed": not problems, "problems": problems, "claims_cited": sorted(cited)}


def run(con, client, run_id, phase, budget, out_dir, ranking, issues, verify_report, records_counts):
    out_dir = Path(out_dir)
    claims = build_claims(ranking, C.MEMO_TOP_ISSUES)
    with (out_dir / "claims.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["claim_id", "issue_id", "metric", "value"])
        w.writeheader()
        w.writerows(claims)
    membership = {m["review_id"]: m["issue_id"] for m in csv.DictReader((out_dir / "membership.csv").open())}
    pack = build_pack(con, ranking, issues, claims, verify_report, records_counts, membership)
    (out_dir / "evidence_pack.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False))
    payload = json.dumps(pack, ensure_ascii=False)
    key = llm.input_hash("memo", MEMO_CONFIG, payload)
    cached = llm.get_artifact(con, key)
    calls = 0
    if cached is None:
        memo, result = None, None
        feedback = ""
        for attempt in range(1, 3):
            text_in = payload + feedback
            llm.reserve(con, run_id, budget, C.MEMO_MODEL, PROMPT, text_in, C.MEMO_MAX_OUTPUT_TOKENS)
            started = llm.now()
            resp, err, secs = llm.call(client, model=C.MEMO_MODEL, effort=C.MEMO_EFFORT, instructions=PROMPT,
                                       payload=text_in, max_output_tokens=C.MEMO_MAX_OUTPUT_TOKENS,
                                       cache_key=C.MEMO_PROMPT_VERSION)
            calls += 1
            memo = resp.output_text if resp is not None and resp.status == "completed" else None
            result = check(memo, pack, claims, ranking) if memo else {"passed": False, "problems": ["no output"]}
            llm.log_call(con, run_id=run_id, role="memo", phase=phase, model=C.MEMO_MODEL, effort=C.MEMO_EFFORT,
                         config=MEMO_CONFIG, batch_no=1, attempt=attempt, review_ids=[], resp=resp,
                         error=err or (None if result["passed"] else "; ".join(result["problems"])[:500]),
                         ok=result["passed"], n_valid=int(result["passed"]), seconds=secs, started=started)
            if result["passed"] or (err is not None and llm.is_fatal(err)):
                break
            feedback = ("\n\nYOUR PREVIOUS DRAFT FAILED THESE AUTOMATED CHECKS - rewrite it and fix them:\n- "
                        + "\n- ".join(result["problems"]))
        cached = {"memo": memo, "check": result, "attempts": calls}
        if memo:
            llm.put_artifact(con, key, "memo", MEMO_CONFIG, cached)
    if cached["memo"]:
        (out_dir / "memo.md").write_text(cached["memo"])
    (out_dir / "memo_check.json").write_text(json.dumps({"config": MEMO_CONFIG, **cached["check"]}, indent=2))
    print(f"  memo: check {'PASSED' if cached['check']['passed'] else 'FAILED'}, {calls} new calls"
          + ("" if cached["check"]["passed"] else f" | {cached['check']['problems'][:3]}"))
    return {"new_model_calls": calls, "check": cached["check"]}
