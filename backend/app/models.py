"""Database models. UUID primary keys, per-user ownership on meetings."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    meetings = relationship("Meeting", back_populates="owner", cascade="all, delete-orphan")


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String(36), primary_key=True, default=_uuid)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False, default="Untitled meeting")
    source_type = Column(String(50), nullable=False, default="upload")  # upload | recording
    language = Column(String(20), nullable=True)  # e.g. 'en', 'auto'
    status = Column(String(50), nullable=False, default="created")
    # created, uploaded, queued, processing, transcribed, summarizing, completed, failed, cancelled
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    deleted_at = Column(DateTime, nullable=True)
    owner = relationship("User", back_populates="meetings")
    recordings = relationship("Recording", back_populates="meeting", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="meeting", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="meeting", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="meeting", cascade="all, delete-orphan")


class Recording(Base):
    __tablename__ = "recordings"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False)  # opaque key, never a public URL
    original_filename = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_now)
    meeting = relationship("Meeting", back_populates="recordings")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    kind = Column(String(50), nullable=False, default="process")  # process | summary | export
    status = Column(String(50), nullable=False, default="created")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    meeting = relationship("Meeting", back_populates="jobs")


class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, default="import")
    model_name = Column(String(100), nullable=True)
    detected_language = Column(String(20), nullable=True)
    full_text = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=_now)
    meeting = relationship("Meeting", back_populates="transcripts")
    segments = relationship("TranscriptSegment", back_populates="transcript",
                            cascade="all, delete-orphan", order_by="TranscriptSegment.segment_index")


class Speaker(Base):
    __tablename__ = "speakers"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    speaker_label = Column(String(50), nullable=False)  # e.g. "Speaker 1"
    display_name = Column(String(255), nullable=True)
    meeting = relationship("Meeting", back_populates="speakers")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id = Column(String(36), primary_key=True, default=_uuid)
    transcript_id = Column(String(36), ForeignKey("transcripts.id"), nullable=False, index=True)
    speaker_id = Column(String(36), ForeignKey("speakers.id"), nullable=True)
    start_seconds = Column(Float, nullable=False, default=0.0)
    end_seconds = Column(Float, nullable=False, default=0.0)
    text = Column(Text, nullable=False, default="")
    confidence = Column(Float, nullable=True)
    segment_index = Column(Integer, nullable=False, default=0)
    transcript = relationship("Transcript", back_populates="segments")


class Summary(Base):
    __tablename__ = "summaries"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, default="local-heuristic")
    model_name = Column(String(100), nullable=True)
    overview = Column(Text, nullable=False, default="")
    key_points_json = Column(Text, nullable=False, default="[]")
    decisions_json = Column(Text, nullable=False, default="[]")
    unresolved_questions_json = Column(Text, nullable=False, default="[]")
    follow_up_email = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    meeting = relationship("Meeting", back_populates="summaries")


class ActionItem(Base):
    __tablename__ = "action_items"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    task = Column(Text, nullable=False)
    owner_text = Column(String(255), nullable=True)  # null unless explicitly stated
    due_date = Column(String(100), nullable=True)  # null unless explicitly stated
    status = Column(String(50), nullable=False, default="open")
    evidence_segment_ids_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=_now)
    meeting = relationship("Meeting", back_populates="action_items")


class MeetingChat(Base):
    __tablename__ = "meeting_chat"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    evidence_segment_ids_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=_now)


class Export(Base):
    __tablename__ = "exports"
    id = Column(String(36), primary_key=True, default=_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    format = Column(String(20), nullable=False)  # txt | json | pdf
    storage_key = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False, default="ready")
    created_at = Column(DateTime, default=_now)
    meeting = relationship("Meeting", back_populates="exports")
