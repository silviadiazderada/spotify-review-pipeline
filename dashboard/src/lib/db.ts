import "server-only";
import { neon } from "@neondatabase/serverless";

// Server-side only: the read-only connection string never reaches the browser.
const url = process.env.DATABASE_URL;
if (!url) throw new Error("DATABASE_URL is not set");
export const sql = neon(url);

export async function output<T = unknown>(key: string): Promise<T | null> {
  const rows = await sql.query("SELECT content FROM outputs WHERE key = $1", [key]);
  return rows.length ? (rows[0].content as T) : null;
}
