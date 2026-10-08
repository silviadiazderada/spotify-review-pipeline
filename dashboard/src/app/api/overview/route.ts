import { connection } from "next/server";
import { sql, output } from "@/lib/db";

// Overall metrics, decision-area totals, cross-area themes, comparable-period trend and monthly series.
export async function GET() {
  await connection(); // read the database at request time, never at build time
  const [status, intents, areas, monthly, pack, run] = await Promise.all([
    sql.query("SELECT status, reason, COUNT(*)::int AS n FROM reviews GROUP BY status, reason ORDER BY n DESC"),
    sql.query("SELECT intent, COUNT(*)::int AS n FROM reviews WHERE status = 'completed' GROUP BY intent ORDER BY n DESC"),
    sql.query(`SELECT area, COUNT(*)::int AS complaints, SUM(severity)::int AS severity_sum
               FROM reviews WHERE status = 'completed' AND intent IN ('complaint','cancellation')
               GROUP BY area ORDER BY severity_sum DESC`),
    sql.query("SELECT month, area, completed, complaints FROM monthly ORDER BY month, area"),
    output<Record<string, unknown>>("evidence_pack"),
    output<Record<string, unknown>>("full_run_cost"),
  ]);
  return Response.json({ status, intents, areas, monthly, pack, cost: run });
}
