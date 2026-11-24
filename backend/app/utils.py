"""Audio validation, private storage, and helpers. Never logs audio/transcript text."""
import hashlib
import os
import uuid
import wave

from fastapi import HTTPException

from app.config import settings

ALLOWED_EXTENSIONS = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".webm": "audio/webm"}

# Magic-byte signatures: (offset, bytes)
SIGNATURES = {
    ".wav": [(0, b"RIFF"), (8, b"WAVE")],
    ".mp3": [(0, b"ID3"), (0, b"\xff\xfb"), (0, b"\xff\xf3"), (0, b"\xff\xf2")],
    ".m4a": [(4, b"ftyp")],
    ".webm": [(0, b"\x1a\x45\xdf\xa3")],
}


def validate_audio(filename: str, content: bytes) -> str:
    """Return the validated extension or raise HTTPException. Checks extension,
    size, and file signature (magic bytes) — MIME headers are not trusted."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext or '(none)'}. Allowed: WAV, MP3, M4A, WebM.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Limit is {settings.max_upload_mb} MB.")
    if len(content) < 12:
        raise HTTPException(status_code=400, detail="File too small or empty.")
    sigs = SIGNATURES[ext]
    if not any(content[off:off + len(magic)] == magic for off, magic in sigs):
        raise HTTPException(status_code=400, detail="File signature does not match the claimed audio format.")
    return ext


def storage_root() -> str:
    root = settings.storage_root
    os.makedirs(os.path.join(root, "audio"), exist_ok=True)
    os.makedirs(os.path.join(root, "exports"), exist_ok=True)
    return root


def save_audio(content: bytes, ext: str) -> tuple[str, str]:
    """Save under an opaque uuid key. Returns (storage_key, sha256)."""
    key = f"audio/{uuid.uuid4().hex}{ext}"
    path = os.path.join(storage_root(), key)
    with open(path, "wb") as f:
        f.write(content)
    return key, hashlib.sha256(content).hexdigest()


def audio_path(storage_key: str) -> str:
    return os.path.join(storage_root(), storage_key)


def delete_file(storage_key: str) -> None:
    try:
        os.remove(audio_path(storage_key))
    except FileNotFoundError:
        pass


def wav_duration_seconds(content: bytes) -> float | None:
    """Duration for WAV files via the stdlib wave module; None otherwise."""
    import io
    try:
        with wave.open(io.BytesIO(content), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None
