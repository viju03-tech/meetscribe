"""Grounded Q&A: keyword retrieval over transcript segments.
Returns evidence; says 'insufficient evidence' when nothing matches."""
import re

STOPWORDS = set("""a an the and or but of to in on for with is are was were be been it this that
these those we you they he she i our your their as at by from not no do does did will would
can could should have has had what when where who why how""".split())


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9]+", text)} - STOPWORDS


def answer_question(question: str, segments: list) -> dict:
    """segments: objects with .id, .text, .start_seconds, .end_seconds."""
    qtok = _tokens(question)
    scored = []
    for seg in segments:
        stok = _tokens(seg.text)
        overlap = qtok & stok
        if overlap:
            scored.append((len(overlap), seg))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return {"answer": "Insufficient evidence in this meeting's transcript to answer that question.",
                "evidence_segment_ids": [], "evidence": []}
    top = scored[:3]
    evidence = [{"id": s.id, "text": s.text, "start_seconds": s.start_seconds,
                 "end_seconds": s.end_seconds} for _, s in top]
    answer = "Based on the transcript: " + " ".join(s.text for _, s in top)
    return {"answer": answer, "evidence_segment_ids": [s.id for _, s in top], "evidence": evidence}
