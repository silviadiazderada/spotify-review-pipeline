import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Spotify Review Insights",
  description: "Where should Spotify focus next quarter? 660,622 app reviews classified by a multi-agent pipeline.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <div>
              <h1>Spotify Review Insights</h1>
              <p className="subtitle">660,622 Google Play reviews, May 2022 – Nov 2023 · multi-agent classification pipeline</p>
            </div>
            <nav>
              <Link href="/">Overview</Link>
              <Link href="/issues">Issue ranking</Link>
              <Link href="/method">Method &amp; evaluation</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
