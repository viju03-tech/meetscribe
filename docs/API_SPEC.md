# Proposed API Contract
Base: `/api/v1`

- `GET /health`
- Auth: `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me`
- Meetings: `GET /meetings`, `POST /meetings`, `GET /meetings/{id}`, `PATCH /meetings/{id}`, `DELETE /meetings/{id}`
- Audio: `POST /meetings/{id}/recordings` (multipart), `GET /meetings/{id}/recordings`, `POST /meetings/{id}/process`
- Jobs: `GET /jobs/{job_id}`; optional `WS /api/v1/jobs/{job_id}/events`
- Transcript: `GET /meetings/{id}/transcript`, `PATCH /meetings/{id}/transcript/segments/{segment_id}`
- Speakers: `PATCH /meetings/{id}/speakers/{speaker_id}`
- AI: `POST /meetings/{id}/summary/generate`, `GET /meetings/{id}/summary`, `GET /meetings/{id}/action-items`, `POST /meetings/{id}/chat`
- Exports: `POST /meetings/{id}/exports`, `GET /exports/{export_id}`

Upload success example:
```json
{"meeting_id":"uuid","recording_id":"uuid","job_id":"job-id","status":"queued"}
```

Error example:
```json
{"error":{"code":"UNSUPPORTED_AUDIO_FORMAT","message":"This audio format is not supported."}}
```

Use secure password hashing, short-lived access tokens, refresh-token rotation and appropriate secure cookie handling. Never trust client-supplied user IDs. Enforce ownership/workspace authorization on every resource.
