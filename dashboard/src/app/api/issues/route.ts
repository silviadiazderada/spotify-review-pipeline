import { connection } from "next/server";
import { sql } from "@/lib/db";

// Baseline ranking: priority = complaint_count x mean_severity = severity_sum (computed by the pipeline in code).
export async function GET() {
  await connection(); // read the database at request time, never at build time
  const issues = await sql.query(
    `SELECT issue_id, topic, subtopic, area, name, description, rank, complaint_count, severity_sum,
            mean_severity::text AS mean_severity, priority_score
     FROM issues ORDER BY rank`);
  return Response.json({ issues });
}
