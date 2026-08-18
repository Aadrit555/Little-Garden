"""
Real minimum-viable auth for public deployment: a single shared API key
checked on every request via the X-API-Key header. This is NOT
per-learner auth (no login, no sessions, no user-owns-their-data
enforcement) — it's a real gate that stops the API being wide open to
the internet, appropriate for a small-scale personal/beta deployment.

If API_KEY is unset (local dev, no .env), the check is skipped entirely
and a clear warning is logged — this keeps local `uvicorn --reload`
testing frictionless while still forcing a real key once deployed
(docker-compose.yml requires API_KEY to be set for the container to
even start).

Real next step beyond this MVP gate: per-learner login (e.g. real
password hashing + JWT sessions, or an OAuth provider) so learners can
only ever read/write their own submissions — needed before any
multi-user public launch beyond a small trusted group.
"""
import os
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("security")

API_KEY = os.environ.get("API_KEY", "")
EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

if not API_KEY:
    logger.warning(
        "API_KEY is not set — running WITHOUT auth. Fine for local dev "
        "on your own machine, NOT fine for any deployment reachable "
        "over a network. Set API_KEY before deploying (see .env.example)."
    )


async def enforce_api_key(request: Request, call_next):
    if not API_KEY or request.url.path in EXEMPT_PATHS:
        return await call_next(request)

    provided = request.headers.get("X-API-Key", "")
    if provided != API_KEY:
        return JSONResponse({"detail": "Missing or invalid X-API-Key header"}, status_code=401)

    return await call_next(request)
