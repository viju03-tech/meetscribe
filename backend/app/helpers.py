"""Shared helpers: ownership-scoped meeting lookup."""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Meeting, User
from app.security import get_current_user


def get_owned_meeting(meeting_id: str, db: Session, user: User) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your meeting")
    return meeting
