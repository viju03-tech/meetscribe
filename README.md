# MeetScribe — AI Meeting Assistant

**Live website:** https://viju03-tech.github.io/meetscribe/

Multilingual meeting assistant: audio upload + live browser recording, transcription,
optional speaker diarization, grounded AI summaries, action items, meeting search,
grounded Q&A, and TXT / JSON / PDF exports. Premium black + crimson theme.

## Quick start (Windows PowerShell)

```powershell
# Backend
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload

# Frontend (another terminal)
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 · API http://localhost:8000 · API docs http://localhost:8000/docs

## Docker

```bash
docker compose up --build
```

Starts PostgreSQL, Redis, backend, Celery worker and frontend. The worker only
takes over jobs when `CELERY_ENABLED=true` (set in compose for the worker); the
API otherwise processes synchronously in-process.

## API (base `/api/v1`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health + provider config |
| GET | `/api/v1/providers` | Provider state (local vs cloud) |
| POST | `/api/v1/auth/register` | Register (bcrypt + JWT) |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/auth/me` | Current user |
| GET/POST | `/api/v1/meetings` | List (q/status/language) / create |
| GET/PATCH/DELETE | `/api/v1/meetings/{id}` | Get / update / delete (removes audio + exports) |
| POST | `/api/v1/meetings/{id}/recordings` | Multipart audio upload (WAV/MP3/M4A/WebM, 100 MB, magic-byte checked) |
| GET | `/api/v1/meetings/{id}/recordings` | List recordings |
| GET | `/api/v1/meetings/{id}/recordings/{rid}/audio` | Authenticated audio stream (private storage) |
| POST | `/api/v1/meetings/{id}/process` | Transcribe → diarize → summarize (sync; Celery when enabled) |
| GET | `/api/v1/jobs/{job_id}` | Job status |
| POST | `/api/v1/meetings/{id}/transcript/import` | Import plain-text transcript (sentence segments) |
| POST | `/api/v1/meetings/{id}/transcript/import-file` | Import .txt transcript file |
| GET | `/api/v1/meetings/{id}/transcript` | Transcript + segments |
| PATCH | `/api/v1/meetings/{id}/transcript/segments/{sid}` | Edit a segment |
| PATCH | `/api/v1/meetings/{id}/speakers/{sid}` | Rename a speaker |
| POST | `/api/v1/meetings/{id}/summary/generate` | Generate grounded summary |
| GET | `/api/v1/meetings/{id}/summary` | Summary |
| GET | `/api/v1/meetings/{id}/action-items` | Action items |
| POST | `/api/v1/meetings/{id}/chat` | Grounded Q&A (says "insufficient evidence" when nothing matches) |
| POST | `/api/v1/meetings/{id}/exports` | Create export (txt/json/pdf) |
| GET | `/api/v1/exports/{id}` | Download export |

## How the AI works (honest labels)

- **Transcription:** `FasterWhisperAdapter` — uses faster-whisper when installed.
  It is **not** a dependency: without it, `/process` on audio fails with a clear
  error telling you to install it or import a transcript. No fake transcripts, ever.
- **Diarization:** heuristic only (neutral Speaker 1/2 by turn-taking / silence gaps),
  clearly labelled; rename speakers in the UI. Not a speaker-identification model.
- **Summary:** local heuristic by default (overview, key points, decisions, action
  items, unresolved questions, follow-up email draft), all with evidence segment ids.
  Owner/due-date are set **only** when explicitly stated, otherwise null.
  With `SUMMARY_PROVIDER=ollama` it calls Ollama over HTTP and validates the JSON
  with Pydantic, falling back to the heuristic (logged) on failure.
- **Q&A:** keyword retrieval over transcript segments; answers cite evidence and
  say "insufficient evidence" when nothing matches.
- **Cloud:** `CLOUD_AI_ENABLED=false` by default. There is no cloud provider
  adapter in this build and no silent cloud fallback.

## Background jobs

`app/services/jobs.py::enqueue_job` tries Celery when `CELERY_ENABLED=true` and
the broker answers; otherwise it runs the synchronous path in-process. Job states:
`created → uploaded → queued → processing → transcribed → summarizing → completed`,
terminal `failed` / `cancelled`.

## Configuration

See `.env.example`. Key vars: `SECRET_KEY`, `DATABASE_URL` (SQLite default
`sqlite:///./meetscribe.db`, PostgreSQL via URL), `STORAGE_ROOT`, `MAX_UPLOAD_MB`
(default 100), `TRANSCRIPTION_PROVIDER`, `SUMMARY_PROVIDER` (`local`|`ollama`),
`OLLAMA_BASE_URL` / `OLLAMA_MODEL`, `CLOUD_AI_ENABLED`, `CORS_ORIGINS`.

## Migrations

Alembic is configured (`backend/alembic.ini`, `alembic/env.py`, initial revision
`alembic/versions/0001_initial.py`). The app also creates tables on startup for
dev convenience. Apply migrations with:

```bash
cd backend && alembic upgrade head
```

## Tests

```bash
cd backend
pytest -q
```

29 tests: auth, ownership isolation, upload validation (bad format / bad magic bytes /
oversized), transcript import + segment editing, summary extraction (decisions,
owner/due only when stated, unresolved questions), grounded Q&A (evidence +
insufficient-evidence), exports (txt/json/pdf bytes), job status, speaker rename,
audio stream ownership, delete removes stored audio.

## What works / what doesn't (Part 1)

Works: everything above, verified by 29 pytest tests + a live curl run
(register → create → WAV upload → transcript import → summary → chat → exports
txt/json/pdf → process → providers).

Not implemented / not tested in Part 1:
- Real Whisper model download and live transcription (faster-whisper not installed
  in this environment; adapter raises a clear error instead).
- Real diarization model (heuristic only).
- Cloud speech / cloud LLM providers (none included; no silent fallback).
- Alembic migrations applied against a live PostgreSQL (config + initial revision
  exist; only SQLite was exercised).
- Chunked/streaming live transcription (MediaRecorder uploads the finished file).
- Workspaces / team sharing, DOCX export, WebSocket job events (polling instead).
- No end-to-end browser test of the frontend; `next build` was run (see report).
Live demo: https://viju03-tech.github.io/meetscribe/
