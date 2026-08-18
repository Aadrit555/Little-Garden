import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base, engine
from app.routers import writing, reading, listening, speaking, profile, learners, content, dictation
from app.security import enforce_api_key

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="German Language Learning & Evaluation API",
    description="German learning MVP with local inference and reviewed learner content.",
    version="0.1.0",
)

# Real API key gate — enforced only if API_KEY env var is set (see app/security.py).
app.middleware("http")(enforce_api_key)

# ALLOWED_ORIGINS must be a real comma-separated domain list in any
# deployment reachable off your own machine. Falls back to "*" only
# for local dev convenience when the env var isn't set.
_origins_raw = os.environ.get("ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(learners.router)
app.include_router(content.router)
app.include_router(writing.router)
app.include_router(reading.router)
app.include_router(listening.router)
app.include_router(speaking.router)
app.include_router(profile.router)
app.include_router(dictation.router)


@app.get("/health")
def health():
    return {"status": "ok"}
