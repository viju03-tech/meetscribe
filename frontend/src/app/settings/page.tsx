"use client";
import { useEffect, useState } from "react";
import { api, type Providers } from "@/lib/api";

export default function Settings() {
  const [p, setP] = useState<Providers | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.providers().then(setP).catch((e) => setError(String(e)));
  }, []);
  return (
    <div>
      <h1 style={{ fontSize: 28 }}>Settings — providers &amp; privacy</h1>
      <p style={{ color: "#929099" }}>
        MeetScribe is local-first. Audio and transcripts are processed on your own infrastructure
        unless a cloud provider is explicitly enabled — and cloud is never used as a silent fallback.
      </p>
      {error && <p style={{ color: "#f05a6c" }}>{error}</p>}
      {p && (
        <div className="card" style={{ padding: 20 }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              <tr><td style={{ padding: 8, color: "#929099" }}>Transcription provider</td><td style={{ padding: 8 }}>{p.transcription_provider} {p.faster_whisper_available ? "(Faster-Whisper installed — local)" : "(Faster-Whisper NOT installed — use transcript import)"}</td></tr>
              <tr><td style={{ padding: 8, color: "#929099" }}>Summary provider</td><td style={{ padding: 8 }}>{p.summary_provider}{p.summary_provider === "ollama" ? ` — Ollama model ${p.ollama_model}` : " — local heuristic, no model call"}</td></tr>
              <tr><td style={{ padding: 8, color: "#929099" }}>Cloud AI enabled</td><td style={{ padding: 8 }}>{p.cloud_ai_enabled ? "YES — cloud processing is on" : "No — nothing leaves this server"}</td></tr>
              <tr><td style={{ padding: 8, color: "#929099" }}>Ollama configured</td><td style={{ padding: 8 }}>{p.ollama_configured ? "Yes" : "No"}</td></tr>
            </tbody>
          </table>
          <p style={{ color: "#929099", fontSize: 14 }}>
            To use real local transcription, install faster-whisper on the backend host.
            To use Ollama summaries, set SUMMARY_PROVIDER=ollama and run Ollama at the configured host.
            Diarization in this build is a labelled heuristic (Speaker 1 / Speaker 2 by turn-taking),
            not a speaker-identification model — it never identifies real people.
          </p>
        </div>
      )}
      <div className="card" style={{ padding: 20, marginTop: 20 }}>
        <h2 style={{ marginTop: 0 }}>Privacy</h2>
        <ul style={{ color: "#929099" }}>
          <li>Audio is stored privately under an opaque key — there is no public URL.</li>
          <li>Deleting a meeting removes its database rows, stored audio and exports.</li>
          <li>No audio or transcript text is written to server logs.</li>
          <li>Recordings require participant consent — the recorder asks you to confirm it.</li>
        </ul>
      </div>
    </div>
  );
}
