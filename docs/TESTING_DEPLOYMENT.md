# Testing and Deployment

## Tests
- Unit: validation, provider routing, schema parsing, summary validation.
- API: upload, job status, transcript retrieval, authorization, deletion.
- Integration: worker + Redis + PostgreSQL + storage.
- UI: recording controls, upload progress, transcript editing, responsive layouts.
- AI evaluation: WER/CER, diarization quality, summary factuality, action-item accuracy.
- Security: oversized upload, MIME spoofing, unauthorized meeting IDs, rate limits.

## Deployment
- Frontend: Vercel or equivalent.
- API and worker: separate containers/processes.
- PostgreSQL and Redis: managed services.
- Audio: private object storage.
- Local inference: GPU-capable worker host, or cloud provider.

Do not use ephemeral local disk for production recordings. Configure migrations, HTTPS, backups, monitoring, queue alerts, retention, and end-to-end deletion. Test a staging deployment before production.
