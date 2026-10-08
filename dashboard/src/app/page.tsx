"use client";

import Link from "next/link";
import { Bars, Loading, Memo, PairBars, Tile, fmt, useApi } from "@/components/ui";

type Overview = {
  status: { status: string; reason: string | null; n: number }[];
  intents: { intent: string; n: number }[];
  areas: { area: string; complaints: number; severity_sum: number }[];
  pack: {
    complaint_and_cancellation_records: number;
    complaints_share_of_completed: string;
    cancellation_intent_records: number;
    cross_area_themes?: Record<string, { complaint_records: number; severity_sum: number; share_of_complaints: string; issues: string[] } | string>;
    volume_spikes?: { average_reviews_per_day_whole_period: number;
      "Jul 6-9 2023": { reviews: number; outside_area_complaints: number; reviews_mentioning_sweden_quran_islam_or_boycott: number };
      "Oct 2023": { outside_area_complaints: number; share_mentioning_update_or_version: string; same_share_Jan_Jun_2023: string } };
    trend_comparable_periods?: Record<string, { completed_reviews: number; complaint_records: number; complaint_share_of_reviews: string; area_share_of_complaints: Record<string, string> } | string>;
  } | null;
  cost: { by_run: { run_id: string; role: string; calls: number; failed: number; cost_usd: number }[] } | null;
};
type Rec = { markdown: string | null; check: { passed: boolean; problems: string[] } | null;
  claims: { claim_id: string; issue_id: string; metric: string; value: string; name: string }[] };
type Issues = { issues: { issue_id: string; name: string; area: string; rank: number; complaint_count: number;
  mean_severity: string; priority_score: number }[] };

const pctNum = (s: string | undefined) => (s ? parseFloat(s) : 0);

export default function OverviewPage() {
  const ov = useApi<Overview>("/api/overview");
  const rec = useApi<Rec>("/api/recommendation");
  const iss = useApi<Issues>("/api/issues");
  if (!ov.data) return <Loading error={ov.error} />;
  const d = ov.data;
  const total = d.status.reduce((a, s) => a + s.n, 0);
  const by = (st: string) => d.status.filter((s) => s.status === st).reduce((a, s) => a + s.n, 0);
  const apiCost = (d.cost?.by_run ?? []).reduce((a, r) => a + Number(r.cost_usd), 0);
  const claims = Object.fromEntries((rec.data?.claims ?? []).map((c) => [c.claim_id, c]));
  const themes = Object.entries(d.pack?.cross_area_themes ?? {}).filter(([k]) => k !== "note") as
    [string, { complaint_records: number; severity_sum: number; share_of_complaints: string; issues: string[] }][];
  const periods = Object.entries(d.pack?.trend_comparable_periods ?? {}).filter(([k]) => k !== "note") as
    [string, { completed_reviews: number; complaint_records: number; complaint_share_of_reviews: string; area_share_of_complaints: Record<string, string> }][];
  const areaNames = periods.length ? Object.keys({ ...periods[0][1].area_share_of_complaints, ...periods[1]?.[1].area_share_of_complaints }) : [];

  return (
    <main>
      <div className="tiles">
        <Tile label="Source reviews" value={fmt(total)} sub="every original ID accounted for" />
        <Tile label="Classified" value={fmt(by("completed"))} sub={`${(Math.floor((100000 * by("completed")) / total) / 1000).toFixed(3)}% of rows`} />
        <Tile label="Quarantined / pending" value={`${fmt(by("quarantined"))} / ${fmt(by("pending"))}`} sub="with recorded reasons" />
        <Tile label="Complaints + cancellations" value={fmt(d.pack?.complaint_and_cancellation_records)}
          sub={`${d.pack?.complaints_share_of_completed ?? "–"} of classified`} />
        <Tile label="Model API spend" value={`$${apiCost.toFixed(2)}`} sub="all roles, full run" />
      </div>

      <section className="card">
        <h2>AI recommendation{" "}
          {rec.data?.check && (rec.data.check.passed
            ? <span className="badge ok">✓ every number and ID verified by code</span>
            : <span className="badge warn">⚠ automated check found problems</span>)}
        </h2>
        <p className="note">Written by the memo agent from saved aggregates and a bounded evidence pack only. Claim chips (C001…)
          link to the issue and show the code-computed value on hover; review IDs open the source review.</p>
        {rec.data?.markdown ? <Memo markdown={rec.data.markdown} claims={claims} /> : <Loading error={rec.error} />}
      </section>

      <div className="grid2">
        <section className="card">
          <h2>Complaint burden by decision area<span className="period">All 18 months</span></h2>
          <p className="note">Severity-weighted complaints (sum of 1–5 severity over complaint and cancellation reviews).</p>
          <Bars rows={d.areas.filter((a) => a.area).map((a) => ({
            label: a.area, value: a.severity_sum, display: fmt(a.severity_sum),
            tip: `${a.area}: ${fmt(a.complaints)} complaints, severity sum ${fmt(a.severity_sum)}`,
          }))} />
        </section>
        <section className="card">
          <h2>Cross-area themes<span className="period">All 18 months</span></h2>
          <p className="note">The shared taxonomy splits free-tier restrictions between billing and usability; these totals add them up.</p>
          <Bars rows={themes.map(([k, t]) => ({
            label: k.replace(/_/g, " "), value: t.severity_sum, display: t.share_of_complaints,
            tip: `${fmt(t.complaint_records)} complaints (${t.share_of_complaints} of all), severity sum ${fmt(t.severity_sum)}`,
          }))} />
          <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>
            Free-tier restrictions = Premium-locked controls + basic features paywalled + shuffle/skip limits.
          </p>
        </section>
      </div>

      {periods.length === 2 && (
        <section className="card">
          <h2>How the complaint mix shifted</h2>
          <p className="note">Share of complaints by area in two comparable 6-month windows (first and last months are partial and
            excluded). Complaints were {periods[0][1].complaint_share_of_reviews} of {fmt(periods[0][1].completed_reviews)} reviews
            in {periods[0][0]} vs {periods[1][1].complaint_share_of_reviews} of {fmt(periods[1][1].completed_reviews)} in {periods[1][0]}.</p>
          <PairBars series={[periods[0][0], periods[1][0]]} rows={areaNames.map((a) => ({
            label: a, a: pctNum(periods[0][1].area_share_of_complaints[a]), b: pctNum(periods[1][1].area_share_of_complaints[a]),
          }))} />
          {d.pack?.volume_spikes && (() => {
            const v = d.pack.volume_spikes!, j = v["Jul 6-9 2023"], o = v["Oct 2023"];
            return (
              <div className="spikes">
                <strong>Why “outside the four areas” jumped:</strong> two events, both in the later window.
                <ul>
                  <li><strong>Jul 6–9, 2023:</strong> {fmt(j.reviews)} reviews in 4 days (average {fmt(v.average_reviews_per_day_whole_period)}/day),
                    {" "}{fmt(j.outside_area_complaints)} of them generic complaints (“Hate this application”, “Worst app”);
                    {" "}{fmt(j.reviews_mentioning_sweden_quran_islam_or_boycott)} mention Sweden, the Quran, Islam or a boycott — consistent with a
                    coordinated boycott campaign (review bombing), not a product change.</li>
                  <li><strong>Oct 2023:</strong> {fmt(o.outside_area_complaints)} generic complaints; {o.share_mentioning_update_or_version} mention an
                    “update” or “version” (vs {o.same_share_Jan_Jun_2023} in Jan–Jun 2023) — consistent with a backlash against an app update
                    that reviewers did not tie to a specific defect.</li>
                </ul>
                Keyword counts are lower bounds; the external causes are not in the data.
              </div>
            );
          })()}
        </section>
      )}

      <section className="card">
        <h2>Top issues by priority score<span className="period">All 18 months</span></h2>
        <p className="note">Baseline ranking: priority = complaint count × mean severity = severity sum. <Link href="/issues">Full ranking →</Link></p>
        {iss.data ? (
          <Bars rows={iss.data.issues.slice(0, 10).map((i) => ({
            label: `${i.rank}. ${i.name}`, value: i.priority_score, display: fmt(i.priority_score), href: `/issues/${i.issue_id}`,
            tip: `${i.issue_id} · ${fmt(i.complaint_count)} complaints × mean severity ${Number(i.mean_severity).toFixed(2)}`,
          }))} />
        ) : <Loading error={iss.error} />}
      </section>
    </main>
  );
}
