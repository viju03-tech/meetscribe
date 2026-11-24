"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, type Meeting } from "@/lib/api";
import Recorder from "@/components/Recorder";

export default function Dashboard() {
  const router = useRouter();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("en");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setMeetings(await api.listMeetings({ q: q || undefined, status: status || undefined }));
    } catch (e) { setError(String(e)); }
  }
  useEffect(() => { if (!getToken()) router.push("/login"); else load(); }, []);

  async function create() {
    if (!title.trim()) return;
    setBusy(true);
    try {
      const m = await api.createMeeting(title.trim(), language);
      router.push(`/meetings/${m.id}`);
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  return (
    <div>
      <h1 style={{ fontSize: 32, margin: "0 0 6px" }}>Your meetings, understood.</h1>
      <p style={{ color: "#929099", marginTop: 0 }}>Upload audio or record live — transcripts, summaries and action items, grounded in evidence.</p>

      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <h2 style={{ marginTop: 0 }}>New meeting</h2>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Meeting title" style={{ flex: 1, minWidth: 200 }} />
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="en">English</option>
            <option value="auto">Auto-detect</option>
            <option value="ta">Tamil</option>
            <option value="hi">Hindi</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
          </select>
          <button className="btn-primary" onClick={create} disabled={busy}>Create meeting</button>
        </div>
        <Recorder />
        {error && <p style={{ color: "#f05a6c" }}>{error}</p>}
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title or transcript…" style={{ flex: 1 }} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="created">Created</option>
          <option value="uploaded">Uploaded</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <button className="btn-ghost" onClick={load}>Search</button>
      </div>

      {meetings.length === 0 ? (
        <div className="card" style={{ padding: 28, color: "#929099" }}>
          No meetings yet. Create one above, then upload audio or paste a transcript to get started.
        </div>
      ) : meetings.map((m) => (
        <a key={m.id} href={`/meetings/${m.id}`} style={{ textDecoration: "none", color: "inherit" }}>
          <div className="card" style={{ padding: 16, marginBottom: 12, display: "flex", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontWeight: 600 }}>{m.title}</div>
              <div style={{ color: "#929099", fontSize: 13 }}>{m.language || "auto"} · {m.created_at?.slice(0, 10) || ""}</div>
            </div>
            <span style={{ color: m.status === "completed" ? "#4ade80" : m.status === "failed" ? "#f05a6c" : "#d9384d", fontSize: 13 }}>{m.status}</span>
          </div>
        </a>
      ))}
    </div>
  );
}
