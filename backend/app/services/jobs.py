"""Job processing: transcribe -> diarize -> summarize.

Celery-ready: enqueue_job() tries Celery/Redis when CELERY_ENABLED=true and
a broker is reachable; otherwise it falls back to the synchronous path
(run_processing) in-process. The sync path is the default in development.
"""
import json
import logging
import os

from sqlalchemy.orm import Session

from app.models import Job, Meeting, Recording, Speaker, Summary, ActionItem, Transcript, TranscriptSegment
from app.providers import (FasterWhisperAdapter, HeuristicDiarizationProvider,
                           TranscriptionUnavailableError)
from app.services import summary_provider
from app.utils import audio_path

logger = logging.getLogger("meetscribe.jobs")

JOB_ORDER = ["created", "uploaded", "queued", "processing", "transcribed", "summarizing", "completed"]


def _set(db: Session, meeting: Meeting, job: Job, status: str, error: str | None = None):
    meeting.status = status
    job.status = status
    if error is not None:
        job.error = error
    db.commit()


def _latest_transcript(db: Session, meeting_id: str):
    return (db.query(Transcript).filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.version.desc()).first())


def _segments_for(db: Session, transcript) -> list[TranscriptSegment]:
    return (db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == transcript.id)
            .order_by(TranscriptSegment.segment_index).all())


def _apply_diarization(db: Session, meeting: Meeting, transcript, segments):
    from app.providers import SegmentResult
    prov = HeuristicDiarizationProvider()
    result = prov.diarize([SegmentResult(s.start_seconds, s.end_seconds, s.text) for s in segments])
    label_to_speaker: dict[str, Speaker] = {}
    for sp in meeting.speakers:
        label_to_speaker[sp.speaker_label] = sp
    for idx, label in result.labels.items():
        if label not in label_to_speaker:
            sp = Speaker(meeting_id=meeting.id, speaker_label=label)
            db.add(sp)
            db.flush()
            label_to_speaker[label] = sp
        segments[idx].speaker_id = label_to_speaker[label].id
    db.commit()


def _persist_summary(db: Session, meeting: Meeting, data: dict):
    # Replace prior summaries + action items for this meeting.
    db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).delete()
    db.query(Summary).filter(Summary.meeting_id == meeting.id).delete()
    db.flush()
    summary = Summary(
        meeting_id=meeting.id,
        provider=data.get("provider", "local-heuristic"),
        model_name=data.get("model_name"),
        overview=data["overview"],
        key_points_json=json.dumps(data["key_points"]),
        decisions_json=json.dumps(data["decisions"]),
        unresolved_questions_json=json.dumps(data["unresolved_questions"]),
        follow_up_email=data.get("follow_up_email"),
    )
    db.add(summary)
    for a in data["action_items"]:
        db.add(ActionItem(meeting_id=meeting.id, task=a["task"],
                          owner_text=a.get("owner_text"), due_date=a.get("due_date"),
                          evidence_segment_ids_json=json.dumps(a.get("evidence_segment_ids", []))))
    db.commit()
    return summary


def run_processing(db: Session, meeting: Meeting, job: Job) -> None:
    """Synchronous processing path. Raises nothing; records failure on the job."""
    try:
        _set(db, meeting, job, "processing")
        transcript = _latest_transcript(db, meeting.id)
        if transcript is None:
            recording = (db.query(Recording).filter(Recording.meeting_id == meeting.id)
                         .order_by(Recording.created_at.desc()).first())
            if recording is None:
                raise RuntimeError("No recording or transcript available to process.")
            # Real transcription attempt — fails clearly without faster-whisper.
            result = FasterWhisperAdapter().transcribe(
                audio_path(recording.storage_key), language=meeting.language)
            transcript = Transcript(meeting_id=meeting.id, provider=result.provider,
                                    model_name=result.model_name,
                                    detected_language=result.detected_language,
                                    full_text=result.full_text, version=1)
            db.add(transcript)
            db.flush()
            for i, seg in enumerate(result.segments):
                db.add(TranscriptSegment(transcript_id=transcript.id, start_seconds=seg.start_seconds,
                                         end_seconds=seg.end_seconds, text=seg.text,
                                         confidence=seg.confidence, segment_index=i))
            db.commit()
        segments = _segments_for(db, transcript)
        if not segments:
            raise RuntimeError("Transcript has no segments.")
        _set(db, meeting, job, "transcribed")
        _apply_diarization(db, meeting, transcript, segments)
        _set(db, meeting, job, "summarizing")
        data = summary_provider.summarize(meeting.id, segments, transcript.full_text)
        _persist_summary(db, meeting, data)
        _set(db, meeting, job, "completed")
    except TranscriptionUnavailableError as exc:
        logger.warning("Processing failed for meeting %s: %s", meeting.id, exc)
        _set(db, meeting, job, "failed", error=str(exc))
    except Exception as exc:  # noqa: BLE001 - record any processing failure
        logger.exception("Processing failed for meeting %s", meeting.id)
        _set(db, meeting, job, "failed", error=str(exc))


def enqueue_job(db: Session, meeting: Meeting, kind: str = "process") -> Job:
    """Create a job row; try Celery when enabled, else run synchronously.
    In this build the sync path is used unless CELERY_ENABLED=true and the
    broker answers — see README 'Background jobs'."""
    job = Job(meeting_id=meeting.id, kind=kind, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    if os.environ.get("CELERY_ENABLED", "").lower() == "true":
        try:
            from app.worker import process_meeting_task  # lazy import
            process_meeting_task.delay(meeting.id, job.id)
            return job
        except Exception as exc:  # noqa: BLE001 - fall back to sync
            logger.warning("Celery enqueue failed (%s); running synchronously", exc)
    run_processing(db, meeting, job)
    return job
