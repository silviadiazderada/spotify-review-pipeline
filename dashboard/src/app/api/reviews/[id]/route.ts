import { connection } from "next/server";
import { sql } from "@/lib/db";

// Trace one review: source ID -> enrichment labels -> issue membership -> ranking.
export async function GET(_req: Request, ctx: RouteContext<"/api/reviews/[id]">) {
  await connection(); // read the database at request time, never at build time
  const { id } = await ctx.params;
  const rows = await sql.query(
    `SELECT r.review_id, r.status, r.reason, r.topic, r.intent, r.severity, r.sentiment, r.needs_review,
            r.evidence_quote, r.entities, r.cache_source_id, r.label_config, r.rating, r.likes, r.app_version,
            r.review_ts::text AS review_ts, r.area, r.issue_id, r.review_text,
            i.name AS issue_name, i.rank AS issue_rank, i.priority_score
     FROM reviews r LEFT JOIN issues i USING (issue_id) WHERE r.review_id = $1`, [id]);
  if (!rows.length) return Response.json({ error: "unknown review" }, { status: 404 });
  return Response.json({ review: rows[0] });
}
