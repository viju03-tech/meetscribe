import os
import tempfile

import pytest

TMP = tempfile.mkdtemp(prefix="meetscribe-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{TMP}/test.db"
os.environ["STORAGE_ROOT"] = os.path.join(TMP, "storage")
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["MAX_UPLOAD_MB"] = "100"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def user_headers(client):
    import uuid
    r = client.post("/api/v1/auth/register",
                    json={"email": f"alice-{uuid.uuid4().hex[:8]}@example.com", "password": "password123",
                          "display_name": "Alice"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def other_headers(client):
    import uuid
    r = client.post("/api/v1/auth/register",
                    json={"email": f"bob-{uuid.uuid4().hex[:8]}@example.com", "password": "password123",
                          "display_name": "Bob"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def meeting(client, user_headers):
    r = client.post("/api/v1/meetings", headers=user_headers,
                    json={"title": "Sprint planning", "language": "en"})
    assert r.status_code == 201, r.text
    return r.json()


def make_wav_bytes(seconds: float = 0.5) -> bytes:
    import io
    import math
    import struct
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        frames = b"".join(struct.pack("<h", int(1000 * math.sin(2 * math.pi * 440 * i / 8000)))
                          for i in range(int(8000 * seconds)))
        w.writeframes(frames)
    return buf.getvalue()
