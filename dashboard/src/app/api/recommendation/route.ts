import { connection } from "next/server";
import { sql, output } from "@/lib/db";

// The AI-generated memo (written by the memo role from saved aggregates only), its automated check,
// and the claim table every issue-level number in it must cite.
export async function GET() {
  await connection(); // read the database at request time, never at build time
  const [memo, check, claims] = await Promise.all([
    output<{ markdown: string }>("memo_md"),
    output<Record<string, unknown>>("memo_check"),
    sql.query(`SELECT c.claim_id, c.issue_id, c.metric, c.value, i.name FROM claims c
               JOIN issues i USING (issue_id) ORDER BY c.claim_id`),
  ]);
  return Response.json({ markdown: memo?.markdown ?? null, check, claims });
}
