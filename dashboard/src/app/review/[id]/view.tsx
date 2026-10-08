"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Loading, useApi } from "@/components/ui";

type Review = { review: Record<string, string | number | boolean | null | string[]> };

export default function View() {
  const { id } = useParams<{ id: string }>();
  const { data, error } = useApi<Review>(`/api/reviews/${id}`);
  if (!data) return <Loading error={error} />;
  const r = data.review;
  const rows: [string, React.ReactNode][] = [
    ["Source review ID", <span key="id" className="mono">{String(r.review_id)}</span>],
    ["Status", `${r.status}${r.reason ? ` (${r.reason})` : ""}`],
    ["Topic / intent", `${r.topic ?? "–"} / ${r.intent ?? "–"}`],
    ["Severity · sentiment", `${r.severity ?? "–"} · ${r.sentiment ?? "–"}`],
    ["Evidence quote", r.evidence_quote ? `“${r.evidence_quote}”` : "–"],
    ["Needs review", String(r.needs_review ?? "–")],
    ["Exact-text reuse of", r.cache_source_id ? <Link key="c" href={`/review/${r.cache_source_id}`} className="mono">{String(r.cache_source_id)}</Link> : "– (labelled by its own call)"],
    ["Label config", <span key="lc" className="mono">{String(r.label_config ?? "–")}</span>],
    ["Issue", r.issue_id ? <Link key="i" href={`/issues/${r.issue_id}`}>{String(r.issue_name)} (#{String(r.issue_rank)}, priority {String(r.priority_score)})</Link> : "– (not a complaint)"],
    ["Source metadata", `${r.rating ?? "–"}★ · ${r.likes ?? 0} likes · app ${r.app_version ?? "unknown"} · ${String(r.review_ts ?? "").slice(0, 16)}`],
  ];
  return (
    <main className="card">
      <h2>Review trace</h2>
      <p className="note">Source ID → enrichment labels → issue membership → ranking. Stars are metadata only; labels come from the text.</p>
      <div className="quote"><div>{String(r.review_text ?? "")}</div></div>
      <dl className="kv">{rows.map(([k, v]) => [<dt key={`${k}-t`}>{k}</dt>, <dd key={`${k}-d`}>{v}</dd>])}</dl>
    </main>
  );
}
