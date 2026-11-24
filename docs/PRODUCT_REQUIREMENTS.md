# Product Requirements

## Vision
Turn meeting recordings into editable, searchable, useful meeting records.

## Main workflow
1. User signs in and creates a meeting.
2. Upload audio or explicitly start browser microphone recording.
3. Backend validates audio and stores it privately.
4. Background worker normalizes audio and transcribes it.
5. Optional diarization assigns neutral labels such as Speaker 1.
6. AI creates a summary, decisions, and action items grounded in transcript evidence.
7. User reviews/edits results, searches, asks questions, exports, or deletes the meeting.

## Features
### Audio
- Upload WAV, MP3, M4A, WebM (formats depend on parser support).
- Browser MediaRecorder; visible recording indicator and consent reminder.
- Preview, cancel, duration/size limits, normalization.

### Transcription
- Automatic or user-selected language.
- Timestamped segments and model/provider metadata.
- Editable transcript and reprocessing.
- Accuracy varies by audio quality, accent, language, and code-switching.

### Speakers
- Diarization estimates speaker turns; it does not identify real people.
- Neutral labels, manual rename/correction, handle overlap as a known limitation.

### AI outputs
- Overview, key points, decisions, action items, unresolved questions, follow-up email draft.
- Owner/deadline only when explicitly stated; otherwise null/unknown.
- Evidence segment IDs or timestamps for decisions and action items.
- Meeting Q&A grounded in transcript passages; say when evidence is insufficient.

### Dashboard/history
- Meeting list, status, duration, language, search/filter, audio player, synchronized transcript.
- Edit title/transcript/speaker labels; delete meeting and associated assets.

### Export/team (later milestones)
- TXT, PDF, DOCX, JSON exports.
- Workspaces, members, roles, sharing, audit trail.

## MVP acceptance
Upload audio -> background transcription -> timestamped transcript -> summary/action items -> meeting history -> delete. Live recording, diarization, chat, team features and advanced exports follow once this pipeline is reliable.
