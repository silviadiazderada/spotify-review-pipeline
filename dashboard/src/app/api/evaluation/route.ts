import { connection } from "next/server";
import { output } from "@/lib/db";

export async function GET() {
  await connection(); // read the database at request time, never at build time
  const keys = ["golden_eval", "verify_report", "planted_gross", "planted_subtle", "injection", "failure_paths",
    "cost_checkpoints", "cost_pilot_runs", "full_run_cost", "run_summary", "memo_check"];
  const values = await Promise.all(keys.map((k) => output(k)));
  return Response.json(Object.fromEntries(keys.map((k, i) => [k, values[i]])));
}
