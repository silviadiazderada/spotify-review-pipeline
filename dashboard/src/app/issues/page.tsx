"use client";

import Link from "next/link";
import { Loading, fmt, useApi } from "@/components/ui";

type Issue = { issue_id: string; name: string; description: string; area: string; rank: number;
  complaint_count: number; severity_sum: number; mean_severity: string; priority_score: number };

export default function IssuesPage() {
  const { data, error } = useApi<{ issues: Issue[] }>("/api/issues");
  if (!data) return <Loading error={error} />;
  const max = Math.max(...data.issues.map((i) => i.priority_score));
  return (
    <main className="card">
      <h2>Baseline issue ranking</h2>
      <p className="note">Each complaint or cancellation review belongs to exactly one issue (topic + rule-based subtopic, assigned in code).
        priority_score = complaint_count × mean_severity = severity_sum; ties break by ascending issue ID. Reproducible offline with
        <code> python -m pipeline rank</code>.</p>
      <div className="table-wrap">
        <table>
          <thead><tr><th className="num">#</th><th>Issue</th><th>Area</th><th className="num">Complaints</th>
            <th className="num">Mean severity</th><th className="num">Priority</th><th style={{ width: "18%" }}></th></tr></thead>
          <tbody>
            {data.issues.map((i) => (
              <tr key={i.issue_id}>
                <td className="num">{i.rank}</td>
                <td><Link href={`/issues/${i.issue_id}`}>{i.name}</Link><div className="muted mono">{i.issue_id}</div></td>
                <td>{i.area}</td>
                <td className="num">{fmt(i.complaint_count)}</td>
                <td className="num">{Number(i.mean_severity).toFixed(2)}</td>
                <td className="num"><strong>{fmt(i.priority_score)}</strong></td>
                <td><div className="inline-bar" style={{ width: `${(100 * i.priority_score) / max}%` }} title={`${fmt(i.priority_score)}`} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
