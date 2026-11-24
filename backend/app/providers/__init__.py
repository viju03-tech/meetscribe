"""Provider interfaces + adapters.

Transcription: FasterWhisperAdapter uses faster-whisper when installed,
otherwise raises a clear TranscriptionUnavailableError — never a fake transcript.
Diarization: HeuristicDiarizationProvider labels neutral Speaker 1/2 by
segment alternation / silence gaps. It is a heuristic, NOT a real model.
Summary: local heuristic (services/summarizer.py) + Ollama HTTP adapter.
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("meetscribe.providers")


class TranscriptionUnavailableError(RuntimeError):
    pass


@dataclass
class SegmentResult:
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None = None


@dataclass
class TranscriptResult:
    segments: list[SegmentResult] = field(default_factory=list)
    detected_language: str | None = None
    provider: str = "faster-whisper"
    model_name: str | None = None

    @property
    def full_text(self) -> str:
        return " ".join(s.text for s in self.segments)


class TranscriptionProvider:
    def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptResult:
        raise NotImplementedError


class FasterWhisperAdapter(TranscriptionProvider):
    """Local Faster-Whisper. Raises a clear error if the package/model is missing."""

    def __init__(self, model: str = "base"):
        self.model = model

    def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscriptionUnavailableError(
                "faster-whisper is not installed. Install it (`pip install faster-whisper`) "
                "and download a model, or import a transcript instead via "
                "POST /api/v1/meetings/{id}/transcript/import."
            ) from exc
        try:
            model = WhisperModel(self.model, device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_path, language=language or None)
        except Exception as exc:
            raise TranscriptionUnavailableError(f"Faster-Whisper transcription failed: {exc}") from exc
        out = [SegmentResult(s.start, s.end, s.text.strip()) for s in segments if s.text.strip()]
        return TranscriptResult(segments=out, detected_language=info.language,
                                provider="faster-whisper", model_name=self.model)


def get_transcription_provider() -> TranscriptionProvider:
    return FasterWhisperAdapter()


# ---- Diarization ----
@dataclass
class DiarizationResult:
    # segment_index -> speaker label ("Speaker 1" / "Speaker 2")
    labels: dict[int, str] = field(default_factory=dict)
    provider: str = "heuristic"
    note: str = "Heuristic diarization (alternation / silence gaps) — not a real speaker model."


class DiarizationProvider:
    def diarize(self, segments: list[SegmentResult]) -> DiarizationResult:
        raise NotImplementedError


class HeuristicDiarizationProvider(DiarizationProvider):
    """Alternates speaker when the gap between segments exceeds 2s or every
    ~3 segments, capped at 2 neutral speakers. Clearly labelled heuristic."""

    def diarize(self, segments: list[SegmentResult]) -> DiarizationResult:
        labels: dict[int, str] = {}
        current = 1
        run = 0
        prev_end: float | None = None
        for i, seg in enumerate(segments):
            gap = None if prev_end is None else seg.start_seconds - prev_end
            if (gap is not None and gap > 2.0) or run >= 3:
                current = 2 if current == 1 else 1
                run = 0
            labels[i] = f"Speaker {current}"
            run += 1
            prev_end = seg.end_seconds
        return DiarizationResult(labels=labels)
