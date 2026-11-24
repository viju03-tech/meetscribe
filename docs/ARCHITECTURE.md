# Technical Architecture

## Components
- **Next.js frontend:** App Router, TypeScript, Tailwind; dashboard, upload/recording, meeting detail, transcript editor, settings; typed API client; polling/WebSocket progress.
- **FastAPI backend:** REST API, auth, Pydantic schemas, SQLAlchemy persistence, authorization, private-storage abstraction.
- **Celery workers:** long-running audio normalization, transcription, diarization, summarization, exports. Redis broker/cache.
- **PostgreSQL:** users, workspaces, meetings, recordings, transcript segments, speakers, summaries, action items, chat, exports.
- **Object storage:** local private folder for development; private S3-compatible bucket in production.

## Upload flow
1. Authenticated multipart upload.
2. Validate size, extension, MIME and file signature; generate opaque storage key.
3. Create meeting/recording metadata; save audio privately.
4. Enqueue Celery job and return job ID.
5. Worker normalizes audio, transcribes, optionally diarizes, persists timestamped segments.
6. Summary job generates validated structured output with evidence references.
7. UI receives job status and displays editable results.

## Live recording
MVP uses browser MediaRecorder. The user explicitly starts/stops recording, sees persistent recording status, then uploads the resulting audio through the same pipeline. Chunked streaming transcription is a later enhancement.

## Hybrid AI interfaces
- `TranscriptionProvider.transcribe(audio_path, language) -> TranscriptResult`
- `DiarizationProvider.diarize(audio_path, transcript) -> DiarizationResult`
- `SummaryProvider.summarize(transcript) -> MeetingSummary`
- `ChatProvider.answer(question, transcript_chunks) -> GroundedAnswer`

Provider selection is configuration-driven. Local: Faster-Whisper and Ollama. Cloud: optional provider adapters. Do not send audio/transcripts to cloud without clear user selection and disclosure. No silent fallback.

## Job states
`created -> uploaded -> queued -> processing -> transcribed -> summarizing -> completed`; terminal alternatives `failed`, `cancelled`.

## Deployment topology
Frontend hosting; separate FastAPI API and Celery worker containers; managed PostgreSQL and Redis; private object storage. Local inference needs sufficient CPU/RAM or a GPU-capable host. A free web host may not have enough resources for local transcription/diarization.
