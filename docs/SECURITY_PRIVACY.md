# Security and Privacy Checklist

- Make recording state visible and obtain participant consent as required by applicable law and policy.
- Clearly disclose whether audio/transcripts are processed locally or transmitted to a cloud provider.
- Enforce upload size/duration limits; allowlist formats; validate MIME and file signatures.
- Generate opaque storage keys; never trust uploaded filenames; keep files outside public web root.
- Consider malware scanning and parser isolation; never pass untrusted filenames into shell commands.
- Hash passwords with Argon2id or bcrypt; authorize every meeting resource; rate-limit login/upload/AI endpoints.
- Keep API keys server-side; use HTTPS; restrict CORS; do not log raw audio, transcript text, tokens or secrets.
- Private by default; provide deletion; define retention and backup policy; encrypt storage/connections where supported.
- Do not infer identity or sensitive characteristics from voices. Summaries are drafts and must be reviewable.
