import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "MeetScribe", description: "Multilingual AI meeting assistant" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header style={{ borderBottom: "1px solid #292930", padding: "14px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <a href="/" style={{ color: "#f4f1f2", textDecoration: "none", fontWeight: 800, letterSpacing: 2 }}>
            <span style={{ color: "#d9384d" }}>MEET</span>SCRIBE
          </a>
          <nav style={{ display: "flex", gap: 18 }}>
            <a href="/" style={{ color: "#929099", textDecoration: "none" }}>Dashboard</a>
            <a href="/settings" style={{ color: "#929099", textDecoration: "none" }}>Settings</a>
            <a href="/login" style={{ color: "#929099", textDecoration: "none" }}>Sign in</a>
          </nav>
        </header>
        <main style={{ maxWidth: 1000, margin: "0 auto", padding: "32px 20px" }}>{children}</main>
      </body>
    </html>
  );
}
