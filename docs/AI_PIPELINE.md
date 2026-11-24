# AI Pipeline

## Transcription
Start with Faster-Whisper locally and a small/base model for development. Return timestamped segments and detected language. Multilingual support and Tamil-English code-switching must be tested with representative recordings. Cloud speech is an optional adapter.

## Diarization
Diarization estimates who spoke when; it does not identify real-world people. Use neutral labels, permit manual correction, test overlapping speech, and review model licensing/access terms before selecting a package.

## Summarization
Generate structured fields: `overview`, `key_points[]`, `decisions[]`, `action_items[]`, `unresolved_questions[]`. Include evidence segment IDs/timestamps. Require owner/deadline to be null unless explicitly stated. Validate with Pydantic. Label summaries as AI-generated drafts.

## Meeting Q&A
Start with transcript chunking and keyword retrieval; later add embeddings/vector search. Return supporting segment/time references. If evidence is insufficient, say so.

## Provider routing
Example settings: `TRANSCRIPTION_PROVIDER=local`, `SUMMARY_PROVIDER=local`, `CLOUD_AI_ENABLED=false`. Cloud processing must be explicitly enabled and disclosed.

## Evaluation
Track Word Error Rate (WER), Character Error Rate (CER), language identification, diarization error rate where feasible, summary factuality, action-item precision/recall, latency and cost per audio minute.
