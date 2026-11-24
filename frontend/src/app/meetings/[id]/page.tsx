"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, getToken, type Meeting, type Segment, type Summary, type Transcript } from "@/lib/api";

export default function MeetingDetail() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recordings, setRecordings] = useState<{ id: string; original_filename?: string | null }[]>([]);
  const [jobStatus, setJobStatus] = useState("");
  const [importText, setImportText] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [speakerNames, setSpeakerNames] = useState<Record<string, string>>({});

  async function load() {
    try {
      setMeeting(await api.getMeeting(id));
      setRecordings(await api.listRecordings(id));
      try { setTranscript(await api.getTranscript(id)); } catch { setTranscript(null); }
      try { setSummary(await api.getSummary(id)); } catch { setSummary(null); }
    } catch (e) { setError(String(e)); }
  }
  useEffect(() => { if (!getToken()) router.push("/login"); else load(); }, []);

  async function uploadFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      const r = await api.uploadRecording(id, f, f.name);
      setJobStatus(`Uploaded — job ${r.job_id} (${r.status})`);
      load();
    } catch (err) { setError(String(err)); }
  }

  async function pollJob(jobId: string) {
    for (let i = 0; i < 30; i++) {
      const j = await api.getJob(jobId);
      setJobStatus(`Job ${j.status}${j.error ? ` — ${j.error}` : ""}`);
      if (j.status === "completed" || j.status === "failed") break;
      await new Promise((r) => setTimeout(r, 1000));
    }
    load();
  }

  async function process() {
    try {
      const r = await api.processMeeting(id);
      setJobStatus(`Processing — ${r.status}`);
      if (r.job_id) pollJob(r.job_id);
      load();
    } catch (e) { setError(String(e)); }
  }

  async function doImport() {
    if (!importText.trim()) return;
    try { await api.importTranscript(id, importText); setImportText(""); load(); }
    catch (e) { setError(String(e)); }
  }

  async function genSummary() {
    try { setSummary(await api.generateSummary(id)); load(); }
    catch (e) { setError(String(e)); }
  }

  async function ask() {
    if (!question.trim()) return;
    try {
      const r = await api.chat(id, question);
      setAnswer(r.answer + (r.evidence_segment_ids.length ? `\n\nEvidence: ${r.evidence_segment_ids.length} segment(s)` : ""));
    } catch (e) { setError(String(e)); }
  }

  async function saveSegment(seg: Segment) {
    const text = editing[seg.id];
    if (text === undefined) return;
    try {
      await api.patchSegment(id, seg.id, { text });
      setEditing((p) => { const n = { ...p }; delete n[seg.id]; return n; });
      load();
    } catch (e) { setError(String(e)); }
  }

  async function renameSpeaker(speakerId: string) {
    const name = speakerNames[speakerId];
    if (!name) return;
    try { await api.renameSpeaker(id, speakerId, name); load(); }
    catch (e) { setError(String(e)); }
  }

  async function exportAs(fmt: "txt" | "json" | "pdf") {
    try {
      const exp = await api.createExport(id, fmt);
      const token = getToken();
      const res = await fetch(api.exportDownloadUrl(exp.id), { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `meetscribe-${id}.${fmt}`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError(String(e)); }
  }

  function seek(seconds: number) {
    if (audioRef.current) { audioRef.current.currentTime = seconds; audioRef.current.play(); }
  }

  if (!meeting) return <p style={{ color: "#929099" }}>Loading…</p>;
  return (
    <div>
      <a href="/" style={{ color: "#929099" }}>← All meetings</a>
      <h1 style={{ fontSize: 28, margin: "8px 0" }}>{meeting.title}</h1>
      <p style={{ color: "#929099" }}>Status: <b style={{ color: "#f4f1f2" }}>{meeting.status}</b> · {meeting.language || "auto"} · {meeting.duration_seconds ? `${meeting.duration_seconds.toFixed(1)}s` : "no audio duration"}</p>
      {error && <p style={{ color: "#f05a6c" }}>{error}</p>}

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h2 style={{ marginTop: 0 }}>Audio</h2>
        {recordings.length > 0 ? (
          <audio ref={audioRef} controls src={api.audioUrl(id, recordings[0].id)} style={{ width: "100%" }} />
        ) : <p style={{ color: "#929099" }}>No recording yet.</p>}
        <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap", alignItems: "center" }}>
          <label className="btn-ghost" style={{ cursor: "pointer" }}>Upload audio (WAV / MP3 / M4A / WebM, max 100 MB)
            <input type="file" accept=".wav,.mp3,.m4a,.webm" onChange={uploadFile} style={{ display: "none" }} />
          </label>
          <button className="btn-primary" onClick={process}>Process (transcribe → summarize)</button>
          {jobStatus && <span style={{ color: "#929099", fontSize: 13 }}>{jobStatus}</span>}
        </div>
        <div style={{ marginTop: 16 }}>
          <p style={{ color: "#929099", fontSize: 14 }}>No audio file? Paste a transcript instead — it becomes timestamped segments you can summarize and search.</p>
          <textarea value={importText} onChange={(e) => setImportText(e.target.value)} rows={4} style={{ width: "100%" }} placeholder="Paste the meeting transcript here…" />
          <button className="btn-ghost" onClick={doImport} style={{ marginTop: 8 }}>Import transcript</button>
        </div>
      </div>

      {transcript && (
        <div className="card" style={{ padding: 20, marginBottom: 20 }}>
          <h2 style={{ marginTop: 0 }}>Transcript <span style={{ color: "#929099", fontSize: 13 }}>({transcript.provider}) — click a segment to seek</span></h2>
          {transcript.segments.map((s) => (
            <div key={s.id} onClick={() => seek(s.start_seconds)} style={{ padding: "8px 0", borderBottom: "1px solid #292930", cursor: "pointer" }}>
              <div style={{ color: "#d9384d", fontSize: 12 }}>
                {Math.floor(s.start_seconds / 60)}:{String(Math.floor(s.start_seconds % 60)).padStart(2, "0")} · {s.speaker_label || "—"}
                {s.speaker_id && (
                  <span onClick={(e) => e.stopPropagation()} style={{ marginLeft: 10 }}>
                    <input value={speakerNames[s.speaker_id] ?? ""} onChange={(e) => setSpeakerNames((p) => ({ ...p, [s.speaker_id!]: e.target.value }))} placeholder="Rename speaker" style={{ padding: "4px 8px", fontSize: 12 }} />
                    <button className="btn-ghost" style={{ padding: "4px 10px", fontSize: 12, marginLeft: 6 }} onClick={() => renameSpeaker(s.speaker_id!)}>Rename</button>
                  </span>
                )}
              </div>
              {editing[s.id] !== undefined ? (
                <span>
                  <input value={editing[s.id]} onChange={(e) => setEditing((p) => ({ ...p, [s.id]: e.target.value }))} style={{ width: "70%" }} />
                  <button className="btn-primary" style={{ padding: "4px 10px", marginLeft: 6 }} onClick={(e) => { e.stopPropagation(); saveSegment(s); }}>Save</button>
                </span>
              ) : (
                <span onDoubleClick={(e) => { e.stopPropagation(); setEditing((p) => ({ ...p, [s.id]: s.text })); }}>{s.text}</span>
              )}
              <span style={{ color: "#929099", fontSize: 12 }}> (double-click to edit)</span>
            </div>
          ))}
        </div>
      )}

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h2 style={{ marginTop: 0 }}>Summary &amp; action items <span style={{ color: "#929099", fontSize: 13 }}>AI-generated draft — review before sharing</span></h2>
        <button className="btn-primary" onClick={genSummary}>Generate summary</button>
        {summary && (
          <div style={{ marginTop: 12 }}>
            <p><b>Overview:</b> {summary.overview}</p>
            <h3>Key points</h3>
            <ul>{summary.key_points.map((k, i) => <li key={i}>{k.text}</li>)}</ul>
            <h3>Decisions</h3>
            <ul>{summary.decisions.map((d, i) => <li key={i}>{d.text}</li>)}</ul>
            <h3>Action items</h3>
            <ul>{summary.action_items.map((a) => (
              <li key={a.id}>{a.task}{a.owner_text ? ` — Owner: ${a.owner_text}` : " — Owner: not stated"}{a.due_date ? ` — Due: ${a.due_date}` : ""}</li>
            ))}</ul>
            <h3>Unresolved questions</h3>
            <ul>{summary.unresolved_questions.map((u, i) => <li key={i}>{u}</li>)}</ul>
            {summary.follow_up_email && <><h3>Follow-up email draft</h3><pre style={{ whiteSpace: "pre-wrap", color: "#929099", background: "#18181e", padding: 12, borderRadius: 8 }}>{summary.follow_up_email}</pre></>}
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <h2 style={{ marginTop: 0 }}>Ask your meeting</h2>
        <div style={{ display: "flex", gap: 10 }}>
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question about this meeting…" style={{ flex: 1 }} />
          <button className="btn-primary" onClick={ask}>Ask</button>
        </div>
        {answer && <p style={{ whiteSpace: "pre-wrap", marginTop: 12 }}>{answer}</p>}
      </div>

      <div className="card" style={{ padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Export &amp; delete</h2>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button className="btn-ghost" onClick={() => exportAs("txt")}>Export TXT</button>
          <button className="btn-ghost" onClick={() => exportAs("json")}>Export JSON</button>
          <button className="btn-ghost" onClick={() => exportAs("pdf")}>Export PDF</button>
          <button className="btn-ghost" style={{ color: "#f05a6c", borderColor: "#d9384d" }} onClick={async () => { if (confirm("Delete this meeting, its audio, transcript and exports?")) { await api.deleteMeeting(id); router.push("/"); } }}>Delete meeting</button>
        </div>
      </div>
    </div>
  );
}
