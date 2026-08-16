# German Learning MVP

Local German learning MVP for Listening, Speaking, Reading, and Writing.

## Core rule

Learner-facing content comes only from reviewed database rows.

- Reading: local LLM generation -> human review -> learner
- Writing: local LLM generation -> human review -> learner
- Listening: real Deutsche Welle audio -> local Whisper transcript -> human review -> learner
- Speaking: real German Common Voice clip + sentence -> human review -> learner
- No seed endpoint
- No fixed German exercise bank
- No fabricated score fallback

## Setup — two real paths

### Path A: Docker (recommended — Speaking works out of the box)

The Docker image bundles Montreal Forced Aligner + the real German
acoustic model + dictionary at build time. Anyone who runs the
container gets working Speaking scoring immediately — no manual MFA
install needed on their end. See "Deploying for real" below.

### Path B: Local, no Docker

Run the setup script once (installs MFA via conda + downloads the real
German models + backend Python deps):

```powershell
# Windows
.\setup.ps1
```
```bash
# Mac/Linux
./setup.sh
```

Requires conda (Miniforge) already installed — the script checks and
tells you where to get it if missing, rather than silently installing
another package manager for you.

Then:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

## Run

From project root:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

FastAPI development server supports auto-reload; keep it local during development.

Open:

```text
frontend/index.html
```

Create learner.

If browser has stale learner state:

```javascript
localStorage.removeItem("german_mvp_learner"); location.reload();
```

## Local LLM

Start Ollama, then inspect installed models:

```powershell
ollama list
```

If exactly one model is installed, app can use it automatically.

If multiple models are installed, choose one explicitly:

```powershell
$env:LOCAL_LLM_MODEL="your-installed-model"
```

If no model is installed, pull one supported by your machine, then set `LOCAL_LLM_MODEL` when multiple models exist.

App makes real local Ollama calls. No cloud grading fallback.

## Content workflow

Open `Content Manager`.

### Reading / Writing

Choose skill, CEFR level, count, then generate.

Generated content starts:

```text
pending
```

Review each item and approve or reject.

Only approved items appear in learner skill screens.

### Listening

Content Manager can ingest real Deutsche Welle audio. Local Whisper creates transcript.

Requirements:

```powershell
ffmpeg -version
```

Whisper model downloads on first use through `faster-whisper`.

### Speaking

Download a German Common Voice dataset and extract it.

In Content Manager, enter extracted dataset folder and ingest clips.

Each clip remains pending until reviewed.

Speaking submission requires:

```powershell
ffmpeg -version
mfa version
```

Set MFA models if their installed names differ:

```powershell
$env:MFA_ACOUSTIC_MODEL="german_mfa"
$env:MFA_DICTIONARY_MODEL="german_mfa"
```

Set `MFA_BIN` if `mfa` is not on PATH.

No MFA fallback score exists. Failure stays a real pipeline error.

## Testing

Run API smoke tests:

```powershell
cd backend
python -m pytest -q
```

FastAPI supports `TestClient` with HTTPX and pytest for API tests.

## End-to-end order

```text
1. Start Ollama
2. Start FastAPI
3. Open frontend
4. Create learner
5. Open Content Manager
6. Generate Reading/Writing
7. Ingest Listening
8. Ingest Speaking
9. Review pending content
10. Approve valid items
11. Test Writing
12. Test Reading
13. Test Listening
14. Test Speaking
```

## What does not work without external/local dependencies

- Reading/Writing generation and grading need Ollama.
- Listening dictation/transcription needs a local Whisper model.
- Speaking needs local Whisper, ffmpeg, MFA, German acoustic model, and German dictionary.

App does not invent output when these dependencies fail.

## Real-time mic feedback

Both the writing dictation button and the speaking record button show
a genuine live audio level meter (Web Audio API `AnalyserNode` reading
the actual mic stream, not a decorative animation), and auto-stop
recording after ~1.8s of real detected silence. This is the practical
"real-time" feature for this MVP — true real-time streaming
transcription (partial results appearing word-by-word while you talk)
would need chunked audio streaming into Whisper, a materially bigger
infra project; noted here honestly as future work rather than faked.

## Deploying for real, beyond your own machine

**Do not run this reachable from the public internet without doing all
of the below.** Everything up to this point assumes localhost-only use.

1. Copy `.env.example` to `.env`, fill in real values:
   - `POSTGRES_PASSWORD` — real random password
   - `ALLOWED_ORIGINS` — the real domain(s) your frontend is served from (never `*`)
   - `API_KEY` — real random secret (`python -c "import secrets; print(secrets.token_urlsafe(32))"`)
2. `docker compose up --build -d` — starts real Postgres + backend (gunicorn, not the dev `--reload` server)
3. Ollama still runs on the host machine (real GPU access needed) — the
   backend container reaches it via `host.docker.internal`, already
   wired in `docker-compose.yml`. MFA + German models are already
   baked into the backend image — Speaking works immediately, no
   separate install step for whoever deploys or uses this.
4. Serve `frontend/index.html` from a real static host (or any web
   server) on the domain you put in `ALLOWED_ORIGINS`.
5. On first load, the app's setup screen has an "API key" field — enter
   the same value as `API_KEY` in `.env`. Stored locally in the
   learner's browser, sent as `X-API-Key` on every request.

**What this deployment setup gives you (real):** Postgres instead of
SQLite, production ASGI serving via gunicorn, restricted CORS, and a
shared-secret API gate stopping the backend being wide open.

**What it deliberately does NOT give you yet (honest gap):**
per-learner login/auth — the current API key is a single shared
secret, not per-user accounts with password/session security. Anyone
with the key can read/write any learner's data. Fine for a small
trusted beta group (e.g. friends testing it), not fine for an open
public signup product — that needs real per-learner auth (password
hashing + sessions, or an OAuth provider) as the next real milestone
before wider launch.
# Dressrosa
