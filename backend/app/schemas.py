"""Pydantic schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None


# ---- Meetings ----
class MeetingCreate(BaseModel):
    title: str = Field(default="Untitled meeting", max_length=500)
    source_type: str = "upload"
    language: Optional[str] = None


class MeetingPatch(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    language: Optional[str] = None
    source_type: Optional[str] = None
    status: Optional[str] = None


class MeetingOut(BaseModel):
    id: str
    title: str
    source_type: str
    language: Optional[str] = None
    status: str
    duration_seconds: Optional[float] = None
    created_at: Optional[str] = None


# ---- Transcript ----
class TranscriptImportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500_000)
    language: Optional[str] = None


class SegmentPatch(BaseModel):
    text: Optional[str] = None
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    speaker_id: Optional[str] = None


class SegmentOut(BaseModel):
    id: str
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = None
    start_seconds: float
    end_seconds: float
    text: str
    confidence: Optional[float] = None
    segment_index: int


class SpeakerRename(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)


# ---- Summary / chat ----
class ActionItemOut(BaseModel):
    id: str
    task: str
    owner_text: Optional[str] = None
    due_date: Optional[str] = None
    status: str
    evidence_segment_ids: list[str] = []


class SummaryOut(BaseModel):
    id: str
    provider: str
    model_name: Optional[str] = None
    overview: str
    key_points: list[dict] = []
    decisions: list[dict] = []
    action_items: list[ActionItemOut] = []
    unresolved_questions: list[str] = []
    follow_up_email: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    evidence_segment_ids: list[str] = []
    evidence: list[SegmentOut] = []


class ExportRequest(BaseModel):
    format: str = Field(pattern="^(txt|json|pdf)$")


class ExportOut(BaseModel):
    id: str
    meeting_id: str
    format: str
    status: str
    download_url: str
