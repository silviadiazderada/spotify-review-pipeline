"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

/** Fetch JSON from the dashboard's own backend API (which reads the database). */
export function useApi<T>(path: string): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    fetch(path)
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
        return r.json();
      })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, [path]);
  return { data, error };
}

export const fmt = (n: number | string | null | undefined) =>
  n === null || n === undefined ? "–" : Number(n).toLocaleString("en-US");

export function Loading({ error }: { error?: string | null }) {
  return <p className="muted">{error ? `Could not load data: ${error}` : "Loading from database…"}</p>;
}

export function Tile({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

/** Single-series horizontal bars (one hue, no legend); hover shows the exact values. */
export function Bars({ rows, color = "var(--series-all)" }: {
  rows: { label: ReactNode; value: number; display: string; tip: string; href?: string }[];
  color?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="bars" role="list">
      {rows.map((r, i) => (
        <div key={i} className="bar-row" role="listitem" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
          <div className="bar-label">{r.href ? <Link href={r.href}>{r.label}</Link> : r.label}</div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(100 * r.value) / max}%`, background: color }} />
          </div>
          <div className="bar-value">{r.display}</div>
          {hover === i && <div className="tip">{r.tip}</div>}
        </div>
      ))}
    </div>
  );
}

/** Two-series comparison (two periods), legend + direct value labels. */
export function PairBars({ rows, series }: {
  rows: { label: string; a: number; b: number }[];
  series: [string, string];
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...rows.flatMap((r) => [r.a, r.b]));
  return (
    <>
      <div className="legend">
        <span><span className="swatch" style={{ background: "var(--series-1)" }} />{series[0]}</span>
        <span><span className="swatch" style={{ background: "var(--series-2)" }} />{series[1]}</span>
      </div>
      <div className="bars">
        {rows.map((r, i) => (
          <div key={r.label} className="bar-row" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
            <div className="bar-label">{r.label}</div>
            <div className="pair">
              <div className="bar-track"><div className="bar-fill" style={{ width: `${(100 * r.a) / max}%`, background: "var(--series-1)" }} /></div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${(100 * r.b) / max}%`, background: "var(--series-2)" }} /></div>
            </div>
            <div className="bar-value">{r.a.toFixed(1)}% → {r.b.toFixed(1)}%</div>
            {hover === i && <div className="tip">{`${r.label}: ${series[0]} ${r.a.toFixed(1)}% · ${series[1]} ${r.b.toFixed(1)}% of complaints`}</div>}
          </div>
        ))}
      </div>
    </>
  );
}

type Claim = { claim_id: string; issue_id: string; metric: string; value: string; name?: string };

const TOKEN = /(\[C\d{3}\]|ISS-[a-z]+-[a-z_]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\*\*[^*]+\*\*)/g;

/** Inline text with traceable links: claim chips, issue links, review links, bold. */
export function Rich({ text, claims }: { text: string; claims: Record<string, Claim> }) {
  const parts = text.split(TOKEN);
  return (
    <>
      {parts.map((p, i) => {
        if (/^\[C\d{3}\]$/.test(p)) {
          const c = claims[p.slice(1, -1)];
          return (
            <Link key={i} href={c ? `/issues/${c.issue_id}` : "#"} className="claim"
              title={c ? `${c.claim_id}: ${c.issue_id} ${c.metric} = ${c.value} (computed in code from saved records)` : "unknown claim"}>
              {p.slice(1, -1)}
            </Link>
          );
        }
        if (/^ISS-/.test(p)) return <Link key={i} href={`/issues/${p}`} className="mono">{p}</Link>;
        if (/^[0-9a-f]{8}-/.test(p)) return <Link key={i} href={`/review/${p}`} className="mono">{p.slice(0, 8)}…</Link>;
        if (/^\*\*/.test(p)) return <strong key={i}>{p.slice(2, -2)}</strong>;
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

/** Minimal Markdown (headings, paragraphs, bullet lists) with traceable inline links. */
export function Memo({ markdown, claims }: { markdown: string; claims: Record<string, Claim> }) {
  const blocks = markdown.split(/\n\s*\n/);
  return (
    <div className="memo">
      {blocks.map((b, i) => {
        const lines = b.split("\n").filter(Boolean);
        if (lines.every((l) => /^\s*[-*] /.test(l)))
          return <ul key={i}>{lines.map((l, j) => <li key={j}><Rich text={l.replace(/^\s*[-*] /, "")} claims={claims} /></li>)}</ul>;
        return lines.map((l, j) => {
          if (l.startsWith("# ")) return <h1 key={`${i}-${j}`}><Rich text={l.slice(2)} claims={claims} /></h1>;
          if (l.startsWith("## ")) return <h2 key={`${i}-${j}`}><Rich text={l.slice(3)} claims={claims} /></h2>;
          if (/^\s*[-*] /.test(l)) return <ul key={`${i}-${j}`}><li><Rich text={l.replace(/^\s*[-*] /, "")} claims={claims} /></li></ul>;
          return <p key={`${i}-${j}`}><Rich text={l} claims={claims} /></p>;
        });
      })}
    </div>
  );
}
