"use client";
import { useRef, useState } from "react";
import { api } from "@/lib/api";

/** Live browser recording via MediaRecorder. The recording is uploaded through
 * the same pipeline as a file upload; nothing is transcribed in the browser. */
export default function Recorder() {
  const [recording, setRecording] = useState(false);
  const [consent, setConsent] = useState(false);
  const [status, setStatus] = useState("");
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function start() {
    if (!consent) { setStatus("Please confirm all participants have consented to being recorded."); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        const title = `Live recording ${new Date().toLocaleString()}`;
        try {
          const m = await api.createMeeting(title, "auto", "recording");
          await api.uploadRecording(m.id, blob, "recording.webm");
          setStatus(`Recording uploaded to “${title}”. Open it from the dashboard to process it.`);
        } catch (e) { setStatus(`Upload failed: ${String(e)}`); }
      };
      mediaRef.current = rec;
      rec.start();
      setRecording(true);
      setStatus("");
    } catch {
      setStatus("Microphone access was denied or unavailable.");
    }
  }

  function stop() {
    mediaRef.current?.stop();
    setRecording(false);
  }

  return (
    <div style={{ marginTop: 16, borderTop: "1px solid #292930", paddingTop: 16 }}>
      <label style={{ display: "flex", gap: 8, alignItems: "center", color: "#929099", fontSize: 14 }}>
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ width: 16, height: 16 }} />
        I confirm all participants have consented to this recording.
      </label>
      <div style={{ display: "flex", gap: 10, marginTop: 12, alignItems: "center" }}>
        {!recording
          ? <button className="btn-primary" onClick={start}>● Start recording</button>
          : <button className="btn-primary" onClick={stop}>■ Stop &amp; upload</button>}
        {recording && <span style={{ display: "flex", gap: 8, alignItems: "center", color: "#f05a6c" }}><span className="rec-dot" /> Recording…</span>}
      </div>
      {status && <p style={{ color: "#929099", fontSize: 14 }}>{status}</p>}
    </div>
  );
}
