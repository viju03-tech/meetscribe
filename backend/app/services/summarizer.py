"""Grounded heuristic summarizer.

Rules (per spec):
- owner / due_date are ONLY set when explicitly stated in the text, else null.
- Every decision / action item / key point carries evidence segment ids.
- Output is labelled an AI-generated draft; it never invents facts.
"""
import json
import re

from app.models import TranscriptSegment

DECISION_PATTERNS = [r"\bdecided\b", r"\bagreed\b", r"\bdecision\b", r"\bwe will go with\b", r"\bapproved\b"]
ACTION_PATTERNS = [r"\baction item\b", r"\btodo\b", r"\bto-do\b", r"\bwill do\b",
                   r"\bwill\s+(?:handle|take|do|own|follow up|send|prepare|review|fix|update)\b",
                   r"\bneeds to\b", r"\bshould\b", r"\bmust\b"]
QUESTION_PATTERNS = [r"\?", r"\bnot sure\b", r"\bunclear\b", r"\bopen question\b", r"\bto be decided\b", r"\btbd\b"]
OWNER_PATTERNS = [
    r"(?:assigned to|owner:?|responsible:?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+will\s+(?:take|handle|do|own|follow up)",
]
DUE_PATTERNS = [
    r"\bby\s+((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|tomorrow|next week|end of (?:the )?(?:week|month|day)|EOD|Friday|today))\b",
    r"\bdue\s+(?:by\s+|on\s+)?(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
    r"\bby\s+(\d{4}-\d{2}-\d{2})\b",
]
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _find(patterns, text):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text.strip()) if s.strip()]


def summarize_segments(segments: list[TranscriptSegment]) -> dict:
    """segments: ORM TranscriptSegment rows (ordered). Returns structured dict."""
    seg_dicts = [{"id": s.id, "text": s.text, "start": s.start_seconds, "end": s.end_seconds}
                 for s in segments]
    full = " ".join(s["text"] for s in seg_dicts)
    sentences = _sentences(full)

    key_points, decisions, actions, questions = [], [], [], []
    for seg in seg_dicts:
        text = seg["text"]
        low = text.lower()
        if any(re.search(p, low) for p in DECISION_PATTERNS):
            decisions.append({"text": text.strip(), "evidence_segment_ids": [seg["id"]]})
        if any(re.search(p, low) for p in ACTION_PATTERNS):
            owner = _find(OWNER_PATTERNS, text)
            due = _find(DUE_PATTERNS, text)
            actions.append({"task": text.strip(), "owner_text": owner, "due_date": due,
                            "evidence_segment_ids": [seg["id"]]})
        if any(re.search(p, low) for p in QUESTION_PATTERNS):
            questions.append(text.strip())
    # Key points: first sentence of each of the first few substantive segments,
    # plus any sentence mentioning a decision/action keyword, de-duplicated.
    seen: set[str] = set()
    for seg in seg_dicts[:8]:
        for sent in _sentences(seg["text"])[:1]:
            if sent not in seen and len(sent) > 10:
                seen.add(sent)
                key_points.append({"text": sent, "evidence_segment_ids": [seg["id"]]})
    if not key_points and sentences:
        key_points = [{"text": sentences[0], "evidence_segment_ids": [seg_dicts[0]["id"]]}]

    overview = sentences[0] if sentences else "No transcript content available."
    if len(sentences) > 1:
        overview = " ".join(sentences[:2])
    email_lines = "\n".join(f"- {kp['text']}" for kp in key_points[:5])
    action_lines = "\n".join(
        f"- {a['task']}" + (f" (Owner: {a['owner_text']})" if a["owner_text"] else "") +
        (f" (Due: {a['due_date']})" if a["due_date"] else "")
        for a in actions[:5]) or "- No explicit action items were stated."
    follow_up = (
        "Subject: Meeting follow-up\n\nHi team,\n\n"
        f"Here is a summary of our meeting: {overview}\n\nKey points:\n{email_lines}\n\n"
        f"Action items:\n{action_lines}\n\nThanks,\nMeetScribe (AI-generated draft — please review before sending)"
    )
    return {
        "overview": overview,
        "key_points": key_points,
        "decisions": decisions,
        "action_items": actions,
        "unresolved_questions": list(dict.fromkeys(questions)),
        "follow_up_email": follow_up,
    }


def to_json(value) -> str:
    return json.dumps(value, ensure_ascii=False)
