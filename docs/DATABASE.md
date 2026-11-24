# Database Design (PostgreSQL + SQLAlchemy + Alembic)

Use UUID primary keys and timestamps. Suggested tables:

- **users:** id, email (unique), password_hash, display_name, created_at, updated_at.
- **workspaces:** id, name, owner_user_id, created_at.
- **workspace_members:** workspace_id, user_id, role (owner/admin/member/viewer), created_at; unique pair.
- **meetings:** id, owner_user_id, workspace_id nullable, title, source_type, language, status, duration_seconds, created_at, updated_at, deleted_at.
- **recordings:** id, meeting_id, storage_key (never public URL), sanitized filename, mime_type, size_bytes, sha256, duration_seconds, created_at.
- **transcripts:** id, meeting_id, provider, model_name, detected_language, full_text, version, created_at.
- **speakers:** id, meeting_id, speaker_label (Speaker 1), display_name nullable.
- **transcript_segments:** id, transcript_id, speaker_id nullable, start_seconds, end_seconds, text, confidence nullable, segment_index.
- **summaries:** id, meeting_id, provider, model_name, overview, key_points JSONB, decisions JSONB, created_at.
- **action_items:** id, meeting_id, task, owner_text nullable, due_date nullable, status, evidence_segment_ids JSONB, created_at.
- **meeting_chat:** id, meeting_id, user_id, question, answer, evidence_segment_ids JSONB, created_at.
- **exports:** id, meeting_id, format, storage_key, status, created_at.

Indexes: meetings(owner_user_id, created_at DESC), transcript_segments(transcript_id, segment_index), action_items(meeting_id, status). Every query must scope meeting access to authenticated user/workspace. Audio belongs in object storage, not database blobs. Deletion must clean dependent records and stored objects.
