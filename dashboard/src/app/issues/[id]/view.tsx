"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Bars, Loading, Tile, fmt, useApi } from "@/components/ui";

type Detail = {
  issue: { issue_id: string; name: string; description: string; area: string; topic: string; subtopic: string; rank: number;
    complaint_count: number; severity_sum: number; mean_severity: string; priority_score: number };
  examples: { review_id: string; severity: number; intent: string; evidence_quote: string; review_text: string; rating: number; review_ts: string }[];
  severity: { severity: number; n: number }[];
  monthly: { month: string; n: number }[];
  claims: { claim_id: string; metric: string; value: string }[];
};

export default function View() {
  const { id } = useParams<{ id: string }>();
  const { data, error } = useApi<Detail>(`/api/issues/${id}`);
  if (!data) return <Loading error={error} />;
  const i = data.issue;
  return (
    <main>
      <p><Link href="/issues">← Issue ranking</Link></p>
      <section className="card">
        <h2>#{i.rank} · {i.name}</h2>
        <p className="note"><span className="mono">{i.issue_id}</span> · area: {i.area} · {i.description}</p>
        <div className="tiles" style={{ marginBottom: 0 }}>
          <Tile label="Complaints" value={fmt(i.complaint_count)} />
          <Tile label="Mean severity" value={Number(i.mean_severity).toFixed(2)} sub={i.mean_severity} />
          <Tile label="Priority score" value={fmt(i.priority_score)} sub="= severity sum" />
        </div>
        {data.claims.length > 0 && (
          <p className="muted" style={{ fontSize: 13 }}>Memo claims: {data.claims.map((c) => `${c.claim_id} ${c.metric}=${c.value}`).join(" · ")}</p>
        )}
      </section>
      <div className="grid2">
        <section className="card">
          <h2>Severity distribution<span className="period">All 18 months</span></h2>
          <p className="note">1 = no problem … 4 = core task blocked, 5 = financial/privacy/data harm.</p>
          <Bars rows={data.severity.map((s) => ({ label: `Severity ${s.severity}`, value: s.n, display: fmt(s.n),
            tip: `${fmt(s.n)} reviews at severity ${s.severity}` }))} />
        </section>
        <section className="card">
          <h2>Complaints per month<span className="period">May 2022 – Nov 2023</span></h2>
          <p className="note">Raw counts; review volume itself varies by month (May 2022 and Nov 2023 are partial).</p>
          <Bars rows={data.monthly.map((m) => ({ label: m.month, value: m.n, display: fmt(m.n), tip: `${m.month}: ${fmt(m.n)} complaints` }))} />
        </section>
      </div>
      <section className="card">
        <h2>Representative reviews</h2>
        <p className="note">Deterministic evidence sample (highest severity first) used by the issue-naming agent.</p>
        {data.examples.map((e) => (
          <div key={e.review_id} className="quote">
            <div>“{e.evidence_quote}”</div>
            <div className="meta"><Link href={`/review/${e.review_id}`} className="mono">{e.review_id.slice(0, 8)}…</Link>
              {" "}· severity {e.severity} · {e.intent} · {e.rating}★ · {e.review_ts?.slice(0, 10)}</div>
          </div>
        ))}
      </section>
    </main>
  );
}
