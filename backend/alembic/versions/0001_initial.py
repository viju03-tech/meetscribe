"""Initial schema — users, meetings, recordings, jobs, transcripts, segments,
speakers, summaries, action items, chat, exports.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _col(name, type_, **kw):
    return sa.Column(name, type_, **kw)


def upgrade() -> None:
    op.create_table("users",
        _col("id", sa.String(36), primary_key=True),
        _col("email", sa.String(255), nullable=False),
        _col("password_hash", sa.String(255), nullable=False),
        _col("display_name", sa.String(255)),
        _col("created_at", sa.DateTime), _col("updated_at", sa.DateTime))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("meetings",
        _col("id", sa.String(36), primary_key=True),
        _col("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        _col("title", sa.String(500), nullable=False),
        _col("source_type", sa.String(50), nullable=False),
        _col("language", sa.String(20)),
        _col("status", sa.String(50), nullable=False),
        _col("duration_seconds", sa.Float),
        _col("created_at", sa.DateTime), _col("updated_at", sa.DateTime),
        _col("deleted_at", sa.DateTime))
    op.create_index("ix_meetings_owner", "meetings", ["owner_user_id"])
    op.create_table("recordings",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("storage_key", sa.String(500), nullable=False),
        _col("original_filename", sa.String(500)), _col("mime_type", sa.String(100)),
        _col("size_bytes", sa.Integer), _col("sha256", sa.String(64)),
        _col("duration_seconds", sa.Float), _col("created_at", sa.DateTime))
    op.create_table("jobs",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("kind", sa.String(50), nullable=False), _col("status", sa.String(50), nullable=False),
        _col("error", sa.Text), _col("created_at", sa.DateTime), _col("updated_at", sa.DateTime))
    op.create_table("transcripts",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("provider", sa.String(50), nullable=False), _col("model_name", sa.String(100)),
        _col("detected_language", sa.String(20)), _col("full_text", sa.Text, nullable=False),
        _col("version", sa.Integer, nullable=False), _col("created_at", sa.DateTime))
    op.create_table("speakers",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("speaker_label", sa.String(50), nullable=False),
        _col("display_name", sa.String(255)))
    op.create_table("transcript_segments",
        _col("id", sa.String(36), primary_key=True),
        _col("transcript_id", sa.String(36), sa.ForeignKey("transcripts.id"), nullable=False),
        _col("speaker_id", sa.String(36), sa.ForeignKey("speakers.id")),
        _col("start_seconds", sa.Float, nullable=False), _col("end_seconds", sa.Float, nullable=False),
        _col("text", sa.Text, nullable=False), _col("confidence", sa.Float),
        _col("segment_index", sa.Integer, nullable=False))
    op.create_table("summaries",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("provider", sa.String(50), nullable=False), _col("model_name", sa.String(100)),
        _col("overview", sa.Text, nullable=False), _col("key_points_json", sa.Text, nullable=False),
        _col("decisions_json", sa.Text, nullable=False),
        _col("unresolved_questions_json", sa.Text, nullable=False),
        _col("follow_up_email", sa.Text), _col("created_at", sa.DateTime))
    op.create_table("action_items",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("task", sa.Text, nullable=False), _col("owner_text", sa.String(255)),
        _col("due_date", sa.String(100)), _col("status", sa.String(50), nullable=False),
        _col("evidence_segment_ids_json", sa.Text, nullable=False),
        _col("created_at", sa.DateTime))
    op.create_table("meeting_chat",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        _col("question", sa.Text, nullable=False), _col("answer", sa.Text, nullable=False),
        _col("evidence_segment_ids_json", sa.Text, nullable=False),
        _col("created_at", sa.DateTime))
    op.create_table("exports",
        _col("id", sa.String(36), primary_key=True),
        _col("meeting_id", sa.String(36), sa.ForeignKey("meetings.id"), nullable=False),
        _col("format", sa.String(20), nullable=False),
        _col("storage_key", sa.String(500), nullable=False),
        _col("status", sa.String(50), nullable=False), _col("created_at", sa.DateTime))


def downgrade() -> None:
    for table in ("exports", "meeting_chat", "action_items", "summaries",
                  "transcript_segments", "speakers", "transcripts", "jobs",
                  "recordings", "meetings", "users"):
        op.drop_table(table)
