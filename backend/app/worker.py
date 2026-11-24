"""Celery worker stub.

Run a worker with:  celery -A app.worker.celery_app worker --loglevel=info
The API falls back to synchronous processing when CELERY_ENABLED is not true
or the broker is unreachable, so the app works fully without Redis/Celery.
"""
import os

from celery import Celery

celery_app = Celery("meetscribe", broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


@celery_app.task(name="meetscribe.process_meeting")
def process_meeting_task(meeting_id: str, job_id: str):
    from app.database import SessionLocal
    from app.models import Job, Meeting
    from app.services.jobs import run_processing
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()
        if meeting and job:
            run_processing(db, meeting, job)
    finally:
        db.close()
