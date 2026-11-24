"""Meetings CRUD + search/filter + recordings + process + delete."""
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.helpers import get_owned_meeting
from app.models import Job, Meeting, Recording, Transcript, TranscriptSegment, User
from app.schemas import MeetingCreate, MeetingOut, MeetingPatch
from app.security import get_current_user
from app.services.jobs import enqueue_job
from app.utils import (audio_path, delete_file, save_audio, validate_audio,
                       wav_duration_seconds)

router = APIRouter(prefix="/meetings", tags=["meetings"])


def _out(m: Meeting) -> MeetingOut:
    return MeetingOut(id=m.id, title=m.title, source_type=m.source_type, language=m.language,
                      status=m.status, duration_seconds=m.duration_seconds,
                      created_at=m.created_at.isoformat() if m.created_at else None)


@router.post("", response_model=MeetingOut, status_code=201)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    m = Meeting(owner_user_id=user.id, title=payload.title,
                source_type=payload.source_type, language=payload.language)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.get("", response_model=list[MeetingOut])
def list_meetings(q: str | None = Query(default=None), status: str | None = None,
                  language: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    query = db.query(Meeting).filter(Meeting.owner_user_id == user.id,
                                     Meeting.deleted_at.is_(None))
    if status:
        query = query.filter(Meeting.status == status)
    if language:
        query = query.filter(Meeting.language == language)
    if q:
        # Search title + transcript text.
        from sqlalchemy import select
        sub = select(Transcript.meeting_id).where(Transcript.full_text.ilike(f"%{q}%"))
        query = query.filter(or_(Meeting.title.ilike(f"%{q}%"), Meeting.id.in_(sub)))
    return [_out(m) for m in query.order_by(Meeting.created_at.desc()).all()]


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    return _out(get_owned_meeting(meeting_id, db, user))


@router.patch("/{meeting_id}", response_model=MeetingOut)
def patch_meeting(meeting_id: str, payload: MeetingPatch, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    for field in ("title", "language", "source_type", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(m, field, value)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    # Remove stored audio + exports from disk first.
    for rec in m.recordings:
        delete_file(rec.storage_key)
    for exp in m.exports:
        delete_file(exp.storage_key)
    db.delete(m)
    db.commit()
    return {"deleted": True, "meeting_id": meeting_id}


@router.post("/{meeting_id}/recordings", status_code=201)
async def upload_recording(meeting_id: str, file: UploadFile = File(...),
                           db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    content = await file.read()
    ext = validate_audio(file.filename or "", content)
    key, sha = save_audio(content, ext)
    duration = wav_duration_seconds(content) if ext == ".wav" else None
    rec = Recording(meeting_id=m.id, storage_key=key,
                    original_filename=file.filename, mime_type=file.content_type,
                    size_bytes=len(content), sha256=sha, duration_seconds=duration)
    db.add(rec)
    m.status = "uploaded"
    if duration:
        m.duration_seconds = duration
    db.commit()
    db.refresh(rec)
    job = Job(meeting_id=m.id, kind="process", status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"meeting_id": m.id, "recording_id": rec.id, "job_id": job.id,
            "status": "queued", "sha256": sha, "size_bytes": len(content),
            "duration_seconds": duration}


@router.get("/{meeting_id}/recordings/{recording_id}/audio")
def stream_recording(meeting_id: str, recording_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Authenticated audio stream — storage is private, never a public URL."""
    from fastapi.responses import FileResponse
    m = get_owned_meeting(meeting_id, db, user)
    rec = db.query(Recording).filter(Recording.id == recording_id,
                                     Recording.meeting_id == m.id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    return FileResponse(audio_path(rec.storage_key), media_type=rec.mime_type or "audio/wav",
                        filename=rec.original_filename or "recording")


@router.get("/{meeting_id}/recordings")
def list_recordings(meeting_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    return [{"id": r.id, "original_filename": r.original_filename, "mime_type": r.mime_type,
             "size_bytes": r.size_bytes, "sha256": r.sha256,
             "duration_seconds": r.duration_seconds, "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in m.recordings]


@router.post("/{meeting_id}/process")
def process_meeting(meeting_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    job = enqueue_job(db, m, kind="process")
    return {"job_id": job.id, "status": job.status, "error": job.error}
