// Typed API client for the MeetScribe backend (/api/v1).
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("meetscribe_token");
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem("meetscribe_token", t);
  else localStorage.removeItem("meetscribe_token");
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: {
      ...(opts.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.body && !(opts.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text.slice(0, 300)}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface Meeting { id: string; title: string; source_type: string; language?: string | null; status: string; duration_seconds?: number | null; created_at?: string | null; }
export interface Segment { id: string; speaker_id?: string | null; speaker_label?: string | null; start_seconds: number; end_seconds: number; text: string; confidence?: number | null; segment_index: number; }
export interface Transcript { transcript_id: string; provider: string; model_name?: string | null; full_text: string; segments: Segment[]; }
export interface ActionItem { id: string; task: string; owner_text?: string | null; due_date?: string | null; status: string; evidence_segment_ids: string[]; }
export interface Summary { id: string; provider: string; model_name?: string | null; overview: string; key_points: { text: string; evidence_segment_ids: string[] }[]; decisions: { text: string; evidence_segment_ids: string[] }[]; action_items: ActionItem[]; unresolved_questions: string[]; follow_up_email?: string | null; }
export interface Providers { transcription_provider: string; summary_provider: string; cloud_ai_enabled: boolean; ollama_configured: boolean; ollama_model: string; faster_whisper_available: boolean; }

export const api = {
  register: (email: string, password: string, display_name?: string) =>
    req<{ access_token: string }>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password, display_name }) }),
  login: (email: string, password: string) =>
    req<{ access_token: string }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => req<{ id: string; email: string; display_name?: string | null }>("/api/v1/auth/me"),
  providers: () => req<Providers>("/api/v1/providers"),
  listMeetings: (params: { q?: string; status?: string; language?: string } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => !!v) as [string, string][]).toString();
    return req<Meeting[]>(`/api/v1/meetings${qs ? `?${qs}` : ""}`);
  },
  createMeeting: (title: string, language?: string, source_type = "upload") =>
    req<Meeting>("/api/v1/meetings", { method: "POST", body: JSON.stringify({ title, language, source_type }) }),
  getMeeting: (id: string) => req<Meeting>(`/api/v1/meetings/${id}`),
  deleteMeeting: (id: string) => req(`/api/v1/meetings/${id}`, { method: "DELETE" }),
  uploadRecording: async (meetingId: string, file: File | Blob, filename: string) => {
    const fd = new FormData();
    fd.append("file", file, filename);
    return req<{ recording_id: string; job_id: string; status: string }>(`/api/v1/meetings/${meetingId}/recordings`, { method: "POST", body: fd });
  },
  listRecordings: (id: string) => req<{ id: string; original_filename?: string | null; size_bytes?: number | null; duration_seconds?: number | null }[]>(`/api/v1/meetings/${id}/recordings`),
  audioUrl: (meetingId: string, recordingId: string) => `${API_BASE}/api/v1/meetings/${meetingId}/recordings/${recordingId}/audio`,
  processMeeting: (id: string) => req<{ job_id: string; status: string; error?: string | null }>(`/api/v1/meetings/${id}/process`, { method: "POST" }),
  getJob: (jobId: string) => req<{ id: string; status: string; error?: string | null }>(`/api/v1/jobs/${jobId}`),
  importTranscript: (id: string, text: string) =>
    req<{ transcript_id: string; segments: number }>(`/api/v1/meetings/${id}/transcript/import`, { method: "POST", body: JSON.stringify({ text }) }),
  getTranscript: (id: string) => req<Transcript>(`/api/v1/meetings/${id}/transcript`),
  patchSegment: (meetingId: string, segmentId: string, patch: Partial<Segment>) =>
    req<Segment>(`/api/v1/meetings/${meetingId}/transcript/segments/${segmentId}`, { method: "PATCH", body: JSON.stringify(patch) }),
  renameSpeaker: (meetingId: string, speakerId: string, display_name: string) =>
    req(`/api/v1/meetings/${meetingId}/speakers/${speakerId}`, { method: "PATCH", body: JSON.stringify({ display_name }) }),
  generateSummary: (id: string) => req<Summary>(`/api/v1/meetings/${id}/summary/generate`, { method: "POST" }),
  getSummary: (id: string) => req<Summary>(`/api/v1/meetings/${id}/summary`),
  getActionItems: (id: string) => req<ActionItem[]>(`/api/v1/meetings/${id}/action-items`),
  chat: (id: string, question: string) =>
    req<{ answer: string; evidence_segment_ids: string[]; evidence: Segment[] }>(`/api/v1/meetings/${id}/chat`, { method: "POST", body: JSON.stringify({ question }) }),
  createExport: (id: string, format: "txt" | "json" | "pdf") =>
    req<{ id: string; download_url: string }>(`/api/v1/meetings/${id}/exports`, { method: "POST", body: JSON.stringify({ format }) }),
  exportDownloadUrl: (exportId: string) => `${API_BASE}/api/v1/exports/${exportId}`,
};
