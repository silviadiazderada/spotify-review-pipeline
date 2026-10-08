"use client";

import { Loading, fmt, useApi } from "@/components/ui";

type Ev = {
  golden_eval: { intent_agreement: number; topic_agreement: number; severity_exact_agreement: number; severity_mae: number;
    sentiment_within_tolerance: number; evidence_quote_exact_substring: number; n_golden: number;
    rule_adjusted_secondary?: { intent_agreement: number; topic_agreement: number; severity_exact_agreement: number } } | null;
  verify_report: { sampled: number; verified: number; agreement: Record<string, number>; severity_mae: number; sample_rule: string } | null;
  planted_gross: { planted: number; detected: number } | null;
  planted_subtle: { planted: number; detected: number } | null;
  injection: { passed: boolean; cases: unknown[] } | null;
  failure_paths: { passed: number; total: number } | null;
  memo_audit: { numbers: number; traced_ok: number; problems: string[] } | null;
  full_run_cost: { by_run: { run_id: string; phase: string; role: string; calls: number; failed: number; cost_usd: number }[] } | null;
};

const pct = (x: number | undefined) => (x === undefined || x === null ? "–" : `${(100 * x).toFixed(0)}%`);

const STAGES: [string, string, string][] = [
  ["1. Prepare", "code", "Read all 660,622 rows, hash every source row, quarantine 13 empty texts, find exact duplicate texts (660,609 → 484,189 distinct)."],
  ["2. Enrich", "model: gpt-6-luna, effort none", "≤50 reviews per request; fixed topic/intent/severity labels, sentiment, exact evidence quote. Code validates every ID and field, retries invalid output once, reuses results for identical text."],
  ["3. Verify", "model: gpt-6-luna, effort low (independent)", "Re-labels a declared random 20% sample (max 2,000) without seeing the first answer; code compares and reports disagreements."],
  ["4. Group", "code + model (names only)", "Code assigns every complaint to one issue (topic + keyword subtopic). A small model only names issues from ≤8 example quotes."],
  ["5. Rank", "code", "priority = complaint count × mean severity = severity sum; deterministic tie-break by issue ID."],
  ["6. Recommend", "model: gpt-6.1-sol, effort low", "Writes the memo from aggregates + bounded evidence pack; code rejects any number, claim ID, issue ID or review ID not in the pack."],
];

export default function MethodPage() {
  const { data, error } = useApi<Ev>("/api/evaluation");
  if (!data) return <Loading error={error} />;
  const g = data.golden_eval, v = data.verify_report;
  const runs = data.full_run_cost?.by_run ?? [];
  const byRole = runs.reduce<Record<string, { calls: number; failed: number; cost: number }>>((a, r) => {
    const x = (a[r.role] ??= { calls: 0, failed: 0, cost: 0 });
    x.calls += Number(r.calls); x.failed += Number(r.failed); x.cost += Number(r.cost_usd);
    return a;
  }, {});
  return (
    <main>
      <section className="card">
        <h2>Pipeline: who does what</h2>
        <p className="note">Code owns IDs, hashing, caching, validation, retries, budgets, membership and arithmetic; models only interpret language.</p>
        <div className="table-wrap"><table>
          <thead><tr><th>Stage</th><th>Owner</th><th>What happens</th></tr></thead>
          <tbody>{STAGES.map(([s, o, w]) => <tr key={s}><td><strong>{s}</strong></td><td>{o}</td><td>{w}</td></tr>)}</tbody>
        </table></div>
      </section>

      <div className="grid2">
        <section className="card">
          <h2>Label quality vs. 50 hand labels</h2>
          <p className="note">Human golden set, frozen before any prediction; n = {g?.n_golden ?? 50} is a diagnostic sample.</p>
          {g ? (
            <table><tbody>
              <tr><td>Intent agreement</td><td className="num">{pct(g.intent_agreement)}</td></tr>
              <tr><td>Topic agreement</td><td className="num">{pct(g.topic_agreement)}</td></tr>
              <tr><td>Severity exact (MAE)</td><td className="num">{pct(g.severity_exact_agreement)} ({g.severity_mae})</td></tr>
              <tr><td>Sentiment within ±0.5</td><td className="num">{pct(g.sentiment_within_tolerance)}</td></tr>
              <tr><td>Evidence quote exact substring</td><td className="num">{g.evidence_quote_exact_substring}/{g.n_golden}</td></tr>
              {g.rule_adjusted_secondary && (
                <tr><td className="muted">Rule-adjusted reference (disclosed, secondary)</td>
                  <td className="num muted">{pct(g.rule_adjusted_secondary.intent_agreement)} / {pct(g.rule_adjusted_secondary.topic_agreement)} / {pct(g.rule_adjusted_secondary.severity_exact_agreement)}</td></tr>
              )}
            </tbody></table>
          ) : <p className="muted">Not loaded.</p>}
        </section>
        <section className="card">
          <h2>Independent verification &amp; system tests</h2>
          <p className="note">{v?.sample_rule ?? ""}</p>
          <table><tbody>
            {v && <tr><td>Verifier agreement (n={fmt(v.verified)}): intent / topic / severity</td>
              <td className="num">{pct(v.agreement.intent)} / {pct(v.agreement.topic)} / {pct(v.agreement.severity)}</td></tr>}
            {data.planted_gross && <tr><td>Planted wrong labels caught (gross)</td><td className="num">{data.planted_gross.detected}/{data.planted_gross.planted}</td></tr>}
            {data.planted_subtle && <tr><td>Planted wrong labels caught (subtle topic shift)</td><td className="num">{data.planted_subtle.detected}/{data.planted_subtle.planted}</td></tr>}
            {data.injection && <tr><td>Prompt-injection test (9 synthetic reviews)</td><td className="num">{data.injection.passed ? "passed" : "failed"}</td></tr>}
            {data.memo_audit && <tr><td>Memo audit: numbers traced to an independent recomputation</td>
              <td className="num">{data.memo_audit.traced_ok}/{data.memo_audit.numbers}</td></tr>}
            {data.failure_paths && <tr><td>Failure-path scenarios (simulated provider)</td><td className="num">{data.failure_paths.passed}/{data.failure_paths.total}</td></tr>}
          </tbody></table>
        </section>
      </div>

      <section className="card">
        <h2>Full-run cost by role</h2>
        <p className="note">Actual usage × dated standard rates; failed attempts included (they cost $0 when the provider refused them).</p>
        <table>
          <thead><tr><th>Role</th><th className="num">Calls</th><th className="num">Failed</th><th className="num">Cost (USD)</th></tr></thead>
          <tbody>{Object.entries(byRole).map(([role, x]) => (
            <tr key={role}><td>{role}</td><td className="num">{fmt(x.calls)}</td><td className="num">{fmt(x.failed)}</td><td className="num">${x.cost.toFixed(2)}</td></tr>
          ))}</tbody>
        </table>
      </section>
    </main>
  );
}
