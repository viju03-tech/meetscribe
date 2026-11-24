"""Exports: real TXT / JSON / PDF generation (reportlab)."""
import json
import os
import uuid

from app.config import settings
from app.utils import storage_root


def _pdf_bytes(title: str, lines: list[str]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    import io
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for line in lines:
        story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), styles["Normal"]))
        story.append(Spacer(1, 6))
    doc.build(story)
    return buf.getvalue()


def build_export(meeting, transcript_text: str, segments: list, summary: dict | None,
                 fmt: str) -> tuple[str, bytes]:
    """Returns (storage_key, file_bytes)."""
    title = f"MeetScribe — {meeting.title}"
    if fmt == "txt":
        parts = [title, "", "TRANSCRIPT", transcript_text]
        if summary:
            parts += ["", "SUMMARY", summary["overview"]]
            parts += ["", "KEY POINTS"] + [f"- {k['text']}" for k in summary["key_points"]]
            parts += ["", "DECISIONS"] + [f"- {d['text']}" for d in summary["decisions"]]
            parts += ["", "ACTION ITEMS"] + [f"- {a['task']}" for a in summary["action_items"]]
        content = "\n".join(parts).encode("utf-8")
    elif fmt == "json":
        payload = {
            "meeting": {"id": meeting.id, "title": meeting.title, "language": meeting.language,
                        "status": meeting.status},
            "transcript": transcript_text,
            "segments": [{"start_seconds": s.start_seconds, "end_seconds": s.end_seconds,
                          "text": s.text} for s in segments],
            "summary": summary,
        }
        content = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    elif fmt == "pdf":
        lines = ["TRANSCRIPT", transcript_text]
        if summary:
            lines += ["", "SUMMARY", summary["overview"]]
            lines += ["KEY POINTS"] + [f"- {k['text']}" for k in summary["key_points"]]
            lines += ["DECISIONS"] + [f"- {d['text']}" for d in summary["decisions"]]
            lines += ["ACTION ITEMS"] + [f"- {a['task']}" for a in summary["action_items"]]
        content = _pdf_bytes(title, lines)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    key = f"exports/{uuid.uuid4().hex}.{fmt}"
    path = os.path.join(storage_root(), key)
    with open(path, "wb") as f:
        f.write(content)
    return key, content
