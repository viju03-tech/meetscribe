"""Summary generation / retrieval, action items, grounded chat, exports, jobs."""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.helpers import get_owned_meeting
from app.models import (ActionItem, Export, Job, MeetingChat, Summary, Transcript,
                        TranscriptSegment, User)
from app.schemas import (ActionItemOut, ChatRequest, ChatResponse, ExportOut,
                         ExportRequest, SummaryOut)
from app.security import get_current_user
from app.services import exports as export_service
from app.services import summary_provider
from app.services.jobs import _persist_summary, _segments_for
from app.services.qa import answer_question
from app.utils import audio_path

router = APIRouter(tags=["ai"])


def _latest_transcript(db: Session, meeting_id: str):
    return (db.query(Transcript).filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.version.desc()).first())


def _summary_out(db: Session, meeting, summary: Summary) -> SummaryOut:
    items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).all()
    return SummaryOut(
        id=summary.id, provider=summary.provider, model_name=summary.model_name,
        overview=summary.overview,
        key_points=json.loads(summary.key_points_json or "[]"),
        decisions=json.loads(summary.decisions_json or "[]"),
        action_items=[ActionItemOut(id=a.id, task=a.task, owner_text=a.owner_text,
                                    due_date=a.due_date, status=a.status,
                                    evidence_segment_ids=json.loads(a.evidence_segment_ids_json or "[]"))
                      for a in items],
        unresolved_questions=json.loads(summary.unresolved_questions_json or "[]"),
        follow_up_email=summary.follow_up_email)


def _summary_dict(summary: Summary, action_items: list[ActionItem]) -> dict:
    return {"overview": summary.overview,
            "key_points": json.loads(summary.key_points_json or "[]"),
            "decisions": json.loads(summary.decisions_json or "[]"),
            "action_items": [{"task": a.task, "owner_text": a.owner_text, "due_date": a.due_date}
                             for a in action_items],
            "unresolved_questions": json.loads(summary.unresolved_questions_json or "[]")}


@router.post("/meetings/{meeting_id}/summary/generate", response_model=SummaryOut)
def generate_summary(meeting_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    tr = _latest_transcript(db, m.id)
    if not tr:
        raise HTTPException(status_code=404, detail="No transcript yet — import one or transcribe audio first")
    segments = _segments_for(db, tr)
    data = summary_provider.summarize(m.id, segments, tr.full_text)
    summary = _persist_summary(db, m, data)
    m.status = "completed"
    db.commit()
    return _summary_out(db, m, summary)


@router.get("/meetings/{meeting_id}/summary", response_model=SummaryOut)
def get_summary(meeting_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    summary = (db.query(Summary).filter(Summary.meeting_id == m.id)
               .order_by(Summary.created_at.desc()).first())
    if not summary:
        raise HTTPException(status_code=404, detail="No summary yet — generate one first")
    return _summary_out(db, m, summary)


@router.get("/meetings/{meeting_id}/action-items", response_model=list[ActionItemOut])
def get_action_items(meeting_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    items = db.query(ActionItem).filter(ActionItem.meeting_id == m.id).all()
    return [ActionItemOut(id=a.id, task=a.task, owner_text=a.owner_text, due_date=a.due_date,
                          status=a.status,
                          evidence_segment_ids=json.loads(a.evidence_segment_ids_json or "[]"))
            for a in items]


@router.post("/meetings/{meeting_id}/chat", response_model=ChatResponse)
def chat(meeting_id: str, payload: ChatRequest, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    tr = _latest_transcript(db, m.id)
    if not tr:
        raise HTTPException(status_code=404, detail="No transcript yet")
    segments = _segments_for(db, tr)
    result = answer_question(payload.question, segments)
    db.add(MeetingChat(meeting_id=m.id, user_id=user.id, question=payload.question,
                       answer=result["answer"],
                       evidence_segment_ids_json=json.dumps(result["evidence_segment_ids"])))
    db.commit()
    from app.schemas import SegmentOut
    evidence = [SegmentOut(id=e["id"], start_seconds=e["start_seconds"],
                           end_seconds=e["end_seconds"], text=e["text"], segment_index=0)
                for e in result["evidence"]]
    return ChatResponse(answer=result["answer"], evidence_segment_ids=result["evidence_segment_ids"],
                        evidence=evidence)


@router.post("/meetings/{meeting_id}/exports", response_model=ExportOut, status_code=201)
def create_export(meeting_id: str, payload: ExportRequest, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    m = get_owned_meeting(meeting_id, db, user)
    tr = _latest_transcript(db, m.id)
    segments = _segments_for(db, tr) if tr else []
    summary = (db.query(Summary).filter(Summary.meeting_id == m.id)
               .order_by(Summary.created_at.desc()).first())
    items = db.query(ActionItem).filter(ActionItem.meeting_id == m.id).all()
    summary_dict = _summary_dict(summary, items) if summary else None
    key, _ = export_service.build_export(
        m, tr.full_text if tr else "", segments, summary_dict, payload.format)
    exp = Export(meeting_id=m.id, format=payload.format, storage_key=key, status="ready")
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return ExportOut(id=exp.id, meeting_id=m.id, format=exp.format, status=exp.status,
                     download_url=f"/api/v1/exports/{exp.id}")


@router.get("/exports/{export_id}")
def download_export(export_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    exp = db.query(Export).filter(Export.id == export_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Export not found")
    get_owned_meeting(exp.meeting_id, db, user)  # ownership check
    media = {"txt": "text/plain", "json": "application/json", "pdf": "application/pdf"}.get(exp.format, "application/octet-stream")
    return FileResponse(audio_path(exp.storage_key), media_type=media,
                        filename=f"meetscribe-export-{exp.id}.{exp.format}")


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    get_owned_meeting(job.meeting_id, db, user)
    return {"id": job.id, "meeting_id": job.meeting_id, "kind": job.kind,
            "status": job.status, "error": job.error,
            "created_at": job.created_at.isoformat() if job.created_at else None}
