"""Transcript import / retrieval / segment edit + speaker rename."""
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.helpers import get_owned_meeting
from app.models import Speaker, Transcript, TranscriptSegment, User
from app.schemas import SegmentOut, SegmentPatch, SpeakerRename, TranscriptImportRequest
from app.security import get_current_user

router = APIRouter(prefix="/meetings", tags=["transcript"])


def _segment_out(seg: TranscriptSegment, label_map: dict) -> SegmentOut:
    label = label_map.get(seg.speaker_id) if seg.speaker_id else None
    return SegmentOut(id=seg.id, speaker_id=seg.speaker_id, speaker_label=label,
                      start_seconds=seg.start_seconds, end_seconds=seg.end_seconds,
                      text=seg.text, confidence=seg.confidence, segment_index=seg.segment_index)


def _latest(db: Session, meeting_id: str):
    return (db.query(Transcript).filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.version.desc()).first())


def _split_into_segments(text: str) -> list[str]:
    """Split plain text into sentence-level chunks for timestamped segments."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _create_transcript(db: Session, meeting_id: str, text: str, language: str | None):
    existing = _latest(db, meeting_id)
    version = (existing.version + 1) if existing else 1
    chunks = _split_into_segments(text)
    tr = Transcript(meeting_id=meeting_id, provider="import", model_name=None,
                    detected_language=language, full_text=text, version=version)
    db.add(tr)
    db.flush()
    for i, chunk in enumerate(chunks):
        db.add(TranscriptSegment(transcript_id=tr.id, start_seconds=float(i * 5),
                                 end_seconds=float(i * 5 + 4.5), text=chunk, segment_index=i))
    db.commit()
    db.refresh(tr)
    return tr, chunks


@router.post("/{meeting_id}/transcript/import", status_code=201)
def import_transcript(meeting_id: str, payload: TranscriptImportRequest,
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    tr, chunks = _create_transcript(db, m.id, payload.text, payload.language)
    if m.status in ("created", "failed"):
        m.status = "transcribed"
        db.commit()
    return {"transcript_id": tr.id, "version": tr.version, "segments": len(chunks)}


@router.post("/{meeting_id}/transcript/import-file", status_code=201)
async def import_transcript_file(meeting_id: str, file: UploadFile = File(...),
                                 db: Session = Depends(get_db),
                                 user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    if not (file.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are accepted for transcript import.")
    raw = await file.read()
    if len(raw) > 500_000:
        raise HTTPException(status_code=413, detail="Transcript file too large.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Transcript file must be UTF-8 text.")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Transcript file is empty.")
    tr, chunks = _create_transcript(db, m.id, text, None)
    return {"transcript_id": tr.id, "version": tr.version, "segments": len(chunks)}


@router.get("/{meeting_id}/transcript")
def get_transcript(meeting_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    tr = _latest(db, m.id)
    if not tr:
        raise HTTPException(status_code=404, detail="No transcript yet for this meeting")
    label_map = {s.id: (s.display_name or s.speaker_label) for s in m.speakers}
    segments = (db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == tr.id)
                .order_by(TranscriptSegment.segment_index).all())
    return {"transcript_id": tr.id, "provider": tr.provider, "model_name": tr.model_name,
            "detected_language": tr.detected_language, "full_text": tr.full_text,
            "version": tr.version,
            "segments": [_segment_out(s, label_map) for s in segments]}


@router.patch("/{meeting_id}/transcript/segments/{segment_id}")
def patch_segment(meeting_id: str, segment_id: str, payload: SegmentPatch,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    tr = _latest(db, m.id)
    if not tr:
        raise HTTPException(status_code=404, detail="No transcript yet")
    seg = db.query(TranscriptSegment).filter(
        TranscriptSegment.id == segment_id,
        TranscriptSegment.transcript_id == tr.id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    if payload.text is not None:
        seg.text = payload.text
    if payload.start_seconds is not None:
        seg.start_seconds = payload.start_seconds
    if payload.end_seconds is not None:
        seg.end_seconds = payload.end_seconds
    if payload.speaker_id is not None:
        seg.speaker_id = payload.speaker_id
    db.commit()
    # Keep full_text in sync.
    segments = (db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == tr.id)
                .order_by(TranscriptSegment.segment_index).all())
    tr.full_text = " ".join(s.text for s in segments)
    db.commit()
    label_map = {s.id: (s.display_name or s.speaker_label) for s in m.speakers}
    return _segment_out(seg, label_map)


@router.patch("/{meeting_id}/speakers/{speaker_id}")
def rename_speaker(meeting_id: str, speaker_id: str, payload: SpeakerRename,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    sp = db.query(Speaker).filter(Speaker.id == speaker_id, Speaker.meeting_id == m.id).first()
    if not sp:
        raise HTTPException(status_code=404, detail="Speaker not found")
    sp.display_name = payload.display_name
    db.commit()
    return {"id": sp.id, "speaker_label": sp.speaker_label, "display_name": sp.display_name}
