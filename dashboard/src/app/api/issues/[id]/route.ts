import { connection } from "next/server";
import { sql } from "@/lib/db";

export async function GET(_req: Request, ctx: RouteContext<"/api/issues/[id]">) {
  await connection(); // read the database at request time, never at build time
  const { id } = await ctx.params;
  const issue = await sql.query(
    `SELECT issue_id, topic, subtopic, area, name, description, rank, complaint_count, severity_sum,
            mean_severity::text AS mean_severity, priority_score, example_review_ids
     FROM issues WHERE issue_id = $1`, [id]);
  if (!issue.length) return Response.json({ error: "unknown issue" }, { status: 404 });
  const [examples, severity, monthly, claims] = await Promise.all([
    sql.query(
      `SELECT review_id, severity, intent, evidence_quote, review_text, rating, review_ts::text AS review_ts
       FROM reviews WHERE review_id = ANY($1::text[])`, [issue[0].example_review_ids]),
    sql.query("SELECT severity, COUNT(*)::int AS n FROM reviews WHERE issue_id = $1 GROUP BY severity ORDER BY severity", [id]),
    sql.query("SELECT review_month AS month, COUNT(*)::int AS n FROM reviews WHERE issue_id = $1 GROUP BY 1 ORDER BY 1", [id]),
    sql.query("SELECT claim_id, metric, value FROM claims WHERE issue_id = $1 ORDER BY claim_id", [id]),
  ]);
  return Response.json({ issue: issue[0], examples, severity, monthly, claims });
}
