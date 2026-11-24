"""MeetScribe API tests: auth, ownership, validation, summary, Q&A, exports."""
import io
import math
import os
import struct
import wave

import pytest


def make_wav_bytes(seconds: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        frames = b"".join(struct.pack("<h", int(1000 * math.sin(2 * math.pi * 440 * i / 8000)))
                          for i in range(int(8000 * seconds)))
        w.writeframes(frames)
    return buf.getvalue()

TEXT = (
    "We decided to launch the new dashboard on Friday. "
    "Priya will handle the release notes by Friday. "
    "The team agreed to use Postgres for the database. "
    "We need to fix the login bug. "
    "Is the pricing page ready? We are not sure about the launch date. "
    "The onboarding flow should be simplified."
)


def _import(client, headers, meeting_id, text=TEXT):
    r = client.post(f"/api/v1/meetings/{meeting_id}/transcript/import",
                    headers=headers, json={"text": text})
    assert r.status_code == 201, r.text
    return r.json()


# ---- Auth ----
def test_register_login_me(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": "carol@example.com", "password": "password123"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    r = client.post("/api/v1/auth/login",
                    json={"email": "carol@example.com", "password": "password123"})
    assert r.status_code == 200 and r.json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["email"] == "carol@example.com"


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register",
                json={"email": "wrongpw@example.com", "password": "password123"})
    r = client.post("/api/v1/auth/login",
                    json={"email": "wrongpw@example.com", "password": "wrongpassword"})
    assert r.status_code == 401


def test_duplicate_register(client):
    client.post("/api/v1/auth/register",
                json={"email": "dup@example.com", "password": "password123"})
    r = client.post("/api/v1/auth/register",
                    json={"email": "dup@example.com", "password": "password123"})
    assert r.status_code == 400


def test_protected_route_requires_auth(client):
    assert client.get("/api/v1/meetings").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


# ---- Meetings CRUD + ownership ----
def test_meeting_crud(client, user_headers):
    r = client.post("/api/v1/meetings", headers=user_headers,
                    json={"title": "Retro", "language": "en"})
    assert r.status_code == 201
    mid = r.json()["id"]
    assert client.get(f"/api/v1/meetings/{mid}", headers=user_headers).status_code == 200
    r = client.patch(f"/api/v1/meetings/{mid}", headers=user_headers, json={"title": "Retro v2"})
    assert r.status_code == 200 and r.json()["title"] == "Retro v2"
    r = client.delete(f"/api/v1/meetings/{mid}", headers=user_headers)
    assert r.status_code == 200 and r.json()["deleted"] is True
    assert client.get(f"/api/v1/meetings/{mid}", headers=user_headers).status_code == 404


def test_ownership_isolation(client, user_headers, other_headers, meeting):
    mid = meeting["id"]
    assert client.get(f"/api/v1/meetings/{mid}", headers=other_headers).status_code == 403
    assert client.patch(f"/api/v1/meetings/{mid}", headers=other_headers,
                        json={"title": "hijack"}).status_code == 403
    assert client.delete(f"/api/v1/meetings/{mid}", headers=other_headers).status_code == 403
    mine = client.get("/api/v1/meetings", headers=other_headers).json()
    assert all(m["id"] != mid for m in mine)


def test_search_filter(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    r = client.get("/api/v1/meetings", headers=user_headers, params={"q": "dashboard"})
    assert r.status_code == 200 and any(m["id"] == meeting["id"] for m in r.json())
    r = client.get("/api/v1/meetings", headers=user_headers, params={"q": "zzzznotfound"})
    assert r.json() == []
    r = client.get("/api/v1/meetings", headers=user_headers, params={"status": "completed"})
    assert r.status_code == 200


# ---- Upload validation ----
def test_upload_valid_wav(client, user_headers, meeting):
    wav = make_wav_bytes()
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                    files={"file": ("test.wav", wav, "audio/wav")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "queued" and body["sha256"] and body["duration_seconds"] is not None
    assert body["duration_seconds"] == pytest.approx(0.5, abs=0.05)


def test_upload_bad_format(client, user_headers, meeting):
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                    files={"file": ("notes.txt", b"hello world, this is text", "text/plain")})
    assert r.status_code == 400


def test_upload_bad_signature(client, user_headers, meeting):
    fake = b"NOT-A-WAVE-FILE" * 10
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                    files={"file": ("fake.wav", fake, "audio/wav")})
    assert r.status_code == 400


def test_upload_oversized(client, user_headers, meeting, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    wav = make_wav_bytes()
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                    files={"file": ("test.wav", wav, "audio/wav")})
    assert r.status_code == 413


def test_upload_other_user_forbidden(client, other_headers, meeting):
    wav = make_wav_bytes()
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=other_headers,
                    files={"file": ("test.wav", wav, "audio/wav")})
    assert r.status_code == 403


# ---- Transcript import + edit ----
def test_transcript_import_and_segments(client, user_headers, meeting):
    out = _import(client, user_headers, meeting["id"])
    assert out["segments"] >= 2
    r = client.get(f"/api/v1/meetings/{meeting['id']}/transcript", headers=user_headers)
    assert r.status_code == 200
    assert "dashboard" in r.json()["full_text"]
    assert len(r.json()["segments"]) == out["segments"]


def test_segment_edit(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    tr = client.get(f"/api/v1/meetings/{meeting['id']}/transcript", headers=user_headers).json()
    seg = tr["segments"][0]
    r = client.patch(f"/api/v1/meetings/{meeting['id']}/transcript/segments/{seg['id']}",
                     headers=user_headers, json={"text": "Edited segment text."})
    assert r.status_code == 200 and r.json()["text"] == "Edited segment text."
    tr2 = client.get(f"/api/v1/meetings/{meeting['id']}/transcript", headers=user_headers).json()
    assert "Edited segment text." in tr2["full_text"]


# ---- Summary ----
def test_summary_decisions_actions_questions(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    r = client.post(f"/api/v1/meetings/{meeting['id']}/summary/generate", headers=user_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["overview"]
    assert any("dashboard" in d["text"].lower() for d in body["decisions"])
    assert any("postgres" in d["text"].lower() for d in body["decisions"])
    assert body["unresolved_questions"], "expected an unresolved question"
    assert body["follow_up_email"]
    assert all(d.get("evidence_segment_ids") for d in body["decisions"])


def test_action_item_owner_due_only_when_stated(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    r = client.post(f"/api/v1/meetings/{meeting['id']}/summary/generate", headers=user_headers)
    items = r.json()["action_items"]
    assert items, "expected action items"
    priya = [a for a in items if "Priya" in a["task"]]
    assert priya and priya[0]["owner_text"] == "Priya"
    assert priya[0]["due_date"] is not None
    # Items without an explicit owner/due must be null, never invented.
    unstated = [a for a in items if "Priya" not in a["task"]]
    for a in unstated:
        assert a["owner_text"] is None
        assert a["due_date"] is None


def test_summary_requires_transcript(client, user_headers, meeting):
    r = client.post(f"/api/v1/meetings/{meeting['id']}/summary/generate", headers=user_headers)
    assert r.status_code == 404


def test_action_items_endpoint(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    client.post(f"/api/v1/meetings/{meeting['id']}/summary/generate", headers=user_headers)
    r = client.get(f"/api/v1/meetings/{meeting['id']}/action-items", headers=user_headers)
    assert r.status_code == 200 and len(r.json()) >= 1


# ---- Processing / diarization / speakers ----
def test_process_with_imported_transcript_completes(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    r = client.post(f"/api/v1/meetings/{meeting['id']}/process", headers=user_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"
    tr = client.get(f"/api/v1/meetings/{meeting['id']}/transcript", headers=user_headers).json()
    assert any(s.get("speaker_label") for s in tr["segments"])


def test_process_without_transcript_fails_clearly(client, user_headers, meeting):
    wav = make_wav_bytes()
    client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                files={"file": ("test.wav", wav, "audio/wav")})
    r = client.post(f"/api/v1/meetings/{meeting['id']}/process", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert "faster-whisper" in (r.json()["error"] or "").lower()


def test_speaker_rename(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    client.post(f"/api/v1/meetings/{meeting['id']}/process", headers=user_headers)
    tr = client.get(f"/api/v1/meetings/{meeting['id']}/transcript", headers=user_headers).json()
    speaker_id = next(s["speaker_id"] for s in tr["segments"] if s.get("speaker_id"))
    r = client.patch(f"/api/v1/meetings/{meeting['id']}/speakers/{speaker_id}",
                     headers=user_headers, json={"display_name": "Alex"})
    assert r.status_code == 200 and r.json()["display_name"] == "Alex"
    tr2 = client.get(f"/api/v1/meetings/{meeting['id']}/transcript", headers=user_headers).json()
    assert any(s.get("speaker_label") == "Alex" for s in tr2["segments"])


def test_job_status_endpoint(client, user_headers, meeting):
    wav = make_wav_bytes()
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                    files={"file": ("test.wav", wav, "audio/wav")})
    job_id = r.json()["job_id"]
    r = client.get(f"/api/v1/jobs/{job_id}", headers=user_headers)
    assert r.status_code == 200 and r.json()["id"] == job_id
    assert client.get("/api/v1/jobs/nonexistent", headers=user_headers).status_code == 404


# ---- Q&A ----
def test_chat_grounded_answer(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    r = client.post(f"/api/v1/meetings/{meeting['id']}/chat", headers=user_headers,
                    json={"question": "What did we decide about the dashboard launch?"})
    assert r.status_code == 200, r.text
    assert r.json()["evidence_segment_ids"]
    assert "dashboard" in r.json()["answer"].lower()


def test_chat_insufficient_evidence(client, user_headers, meeting):
    _import(client, user_headers, meeting["id"])
    r = client.post(f"/api/v1/meetings/{meeting['id']}/chat", headers=user_headers,
                    json={"question": "What is the quantum flux capacitor budget for Mars?"})
    assert r.status_code == 200
    assert "insufficient evidence" in r.json()["answer"].lower()
    assert r.json()["evidence_segment_ids"] == []


# ---- Exports ----
@pytest.mark.parametrize("fmt", ["txt", "json", "pdf"])
def test_exports(client, user_headers, meeting, fmt):
    _import(client, user_headers, meeting["id"])
    client.post(f"/api/v1/meetings/{meeting['id']}/summary/generate", headers=user_headers)
    r = client.post(f"/api/v1/meetings/{meeting['id']}/exports", headers=user_headers,
                    json={"format": fmt})
    assert r.status_code == 201, r.text
    exp_id = r.json()["id"]
    r = client.get(f"/api/v1/exports/{exp_id}", headers=user_headers)
    assert r.status_code == 200
    assert len(r.content) > 100
    if fmt == "pdf":
        assert r.content[:4] == b"%PDF"
    if fmt == "json":
        assert b"dashboard" in r.content


def test_audio_stream_requires_ownership(client, user_headers, other_headers, meeting):
    wav = make_wav_bytes()
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                    files={"file": ("test.wav", wav, "audio/wav")})
    rec_id = r.json()["recording_id"]
    r = client.get(f"/api/v1/meetings/{meeting['id']}/recordings/{rec_id}/audio",
                   headers=user_headers)
    assert r.status_code == 200 and r.content[:4] == b"RIFF"
    assert client.get(f"/api/v1/meetings/{meeting['id']}/recordings/{rec_id}/audio",
                      headers=other_headers).status_code == 403


def test_delete_meeting_removes_audio(client, user_headers, meeting):
    from app.config import settings
    audio_dir = os.path.join(settings.storage_root, "audio")
    before = len(os.listdir(audio_dir)) if os.path.isdir(audio_dir) else 0
    wav = make_wav_bytes()
    r = client.post(f"/api/v1/meetings/{meeting['id']}/recordings", headers=user_headers,
                    files={"file": ("test.wav", wav, "audio/wav")})
    assert r.status_code == 201
    assert len(os.listdir(audio_dir)) == before + 1
    client.delete(f"/api/v1/meetings/{meeting['id']}", headers=user_headers)
    assert len(os.listdir(audio_dir)) == before
