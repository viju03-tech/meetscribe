"""MeetScribe API — FastAPI entrypoint."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.database import Base, engine
from app.routers import ai, auth, meetings, transcript

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meetscribe")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="MeetScribe API", version="0.1.0",
              description="Multilingual AI meeting assistant. Local-first; cloud never used silently.")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _create_tables():
    Base.metadata.create_all(bind=engine)


@app.exception_handler(429)
async def _rate_limit_handler(request: Request, exc):
    return JSONResponse(status_code=429, content={"error": {"code": "RATE_LIMITED",
                                                            "message": "Too many requests. Please slow down."}})


@app.get("/health")
def health():
    return {"status": "ok", "service": "meetscribe-api",
            "transcription_provider": settings.transcription_provider,
            "summary_provider": settings.summary_provider,
            "cloud_ai_enabled": settings.cloud_ai_enabled}


@app.get("/api/v1/providers")
def providers():
    """Provider configuration state — shown on the settings page so users can
    see exactly what runs locally vs what would use the cloud."""
    return {"transcription_provider": settings.transcription_provider,
            "summary_provider": settings.summary_provider,
            "cloud_ai_enabled": settings.cloud_ai_enabled,
            "ollama_configured": bool(settings.ollama_base_url),
            "ollama_model": settings.ollama_model,
            "faster_whisper_available": _whisper_available()}


def _whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


app.include_router(auth.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(transcript.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
