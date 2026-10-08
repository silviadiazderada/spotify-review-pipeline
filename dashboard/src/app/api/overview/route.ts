import { connection } from "next/server";
import { sql, output } from "@/lib/db";

// Overall metrics, decision-area totals, cross-area themes, comparable-period trend and monthly series.
export async function GET() {
  await connection(); // read the database at request time, never at build time
  // Counts are computed once by scripts/load_db.py from the reviews table and stored in `outputs`.
  const [counts, monthly, pack, run] = await Promise.all([
    output<{ status: unknown[]; intents: unknown[]; areas: unknown[] }>("overview_counts"),
    sql.query("SELECT month, area, completed, complaints FROM monthly ORDER BY month, area"),
    output<Record<string, unknown>>("evidence_pack"),
    output<Record<string, unknown>>("full_run_cost"),
  ]);
  const { status = [], intents = [], areas = [] } = counts ?? {};
  return Response.json({ status, intents, areas, monthly, pack, cost: run });
}
