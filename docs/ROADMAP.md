# Implementation Roadmap

1. **Environment/skeleton:** Python venv, FastAPI health endpoint, Next.js app. Acceptance: backend health and frontend both run.
2. **Premium UI shell:** black/crimson tokens, sidebar, dashboard, meeting list, responsive empty/loading/error states.
3. **Audio input:** upload, MediaRecorder, validation, private local storage, meeting metadata.
4. **Transcription:** Redis/Celery, Faster-Whisper adapter, segment persistence, progress updates.
5. **Diarization:** provider adapter, neutral speaker IDs, rename/correct UI.
6. **Hybrid LLM:** Ollama local + optional cloud provider, structured summaries and evidence-linked tasks.
7. **Persistence/auth:** PostgreSQL models, Alembic migrations, secure login, per-user access, deletion.
8. **Advanced:** meeting Q&A, exports, search/filter, analytics, workspaces/sharing.
9. **Hardening/deploy:** tests, file security, rate limits, retention/backups, containers, monitoring, staging and production.

Do not begin the next phase until the current acceptance criteria pass. Build the audio-to-transcript pipeline before adding many optional features.
