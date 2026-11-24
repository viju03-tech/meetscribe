"""Summary provider: local heuristic + Ollama adapter with Pydantic validation
and fallback to heuristic on failure (logged, never a silent cloud claim)."""
import json
import logging
from typing import Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.services import summarizer as heuristic

logger = logging.getLogger("meetscribe.summary")


class OllamaSummary(BaseModel):
    overview: str = ""
    key_points: list[str] = []
    decisions: list[str] = []
    action_items: list[dict] = []
    unresolved_questions: list[str] = []


def _heuristic(meeting_id: str, segments, provider="local-heuristic", model=None) -> dict:
    data = heuristic.summarize_segments(segments)
    data["provider"] = provider
    data["model_name"] = model
    return data


def summarize(meeting_id: str, segments, full_text: str) -> dict:
    """Returns dict with overview/key_points/decisions/action_items/
    unresolved_questions/follow_up_email/provider/model_name."""
    if settings.summary_provider == "ollama":
        try:
            return _ollama_summary(segments, full_text)
        except Exception as exc:  # logged fallback, never silent
            logger.warning("Ollama summary failed (%s); falling back to local heuristic", exc)
    return _heuristic(meeting_id, segments)


def _ollama_summary(segments, full_text: str) -> dict:
    prompt = (
        "Summarize this meeting transcript as JSON with keys: overview (string), "
        "key_points (string list), decisions (string list), action_items "
        "(list of {task, owner_text, due_date} — owner_text/due_date ONLY if explicitly "
        "stated, else null), unresolved_questions (string list). "
        "Do not invent facts. Transcript:\n" + full_text[:12000]
    )
    resp = httpx.post(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        json={"model": settings.ollama_model, "prompt": prompt, "stream": False, "format": "json"},
        timeout=120.0,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "{}")
    try:
        parsed = OllamaSummary.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"Ollama returned invalid summary JSON: {exc}") from exc
    seg_ids = [s.id for s in segments[:1]]
    base = {
        "overview": parsed.overview,
        "key_points": [{"text": t, "evidence_segment_ids": seg_ids} for t in parsed.key_points],
        "decisions": [{"text": t, "evidence_segment_ids": seg_ids} for t in parsed.decisions],
        "action_items": [
            {"task": a.get("task", ""), "owner_text": a.get("owner_text"),
             "due_date": a.get("due_date"), "evidence_segment_ids": seg_ids}
            for a in parsed.action_items],
        "unresolved_questions": parsed.unresolved_questions,
        "follow_up_email": None,
        "provider": "ollama",
        "model_name": settings.ollama_model,
    }
    return base
