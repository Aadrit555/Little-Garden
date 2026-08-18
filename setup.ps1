# Real one-command setup for running the German MVP directly on Windows
# (no Docker). Automates the parts that are genuinely automatable;
# stops with a clear message for the one manual step that isn't safe
# to script silently (installing conda itself).

$ErrorActionPreference = "Stop"

Write-Host "== German MVP setup ==" -ForegroundColor Cyan

# 1. Check conda is available — MFA requires conda (Kaldi binary deps,
#    not available via plain pip). Real requirement, not worked around.
$conda = Get-Command conda -ErrorAction SilentlyContinue
if (-not $conda) {
    Write-Host "conda not found." -ForegroundColor Red
    Write-Host "Install Miniforge first (one-time, real manual step):"
    Write-Host "  https://github.com/conda-forge/miniforge#download"
    Write-Host "Then re-run this script."
    exit 1
}

# 2. Real MFA install via conda-forge (MFA's documented install path)
Write-Host "Installing Montreal Forced Aligner (real, via conda-forge)..." -ForegroundColor Cyan
conda install -y -c conda-forge montreal-forced-aligner
if ($LASTEXITCODE -ne 0) { Write-Host "MFA install failed — see error above." -ForegroundColor Red; exit 1 }

# 3. Real German acoustic model + dictionary download
Write-Host "Downloading real German acoustic model + dictionary..." -ForegroundColor Cyan
mfa model download acoustic german_mfa
mfa model download dictionary german_mfa

# 4. Real backend Python deps
Write-Host "Installing backend Python dependencies..." -ForegroundColor Cyan
pip install -r backend\requirements.txt

# 5. Check Ollama separately — can't silently install a whole other app either
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host ""
    Write-Host "Ollama not found — install from https://ollama.com, then run:" -ForegroundColor Yellow
    Write-Host "  ollama pull llama3.1:8b-instruct-q4_K_M"
} else {
    Write-Host "Ollama found. Checking model is pulled..." -ForegroundColor Cyan
    ollama pull llama3.1:8b-instruct-q4_K_M
}

Write-Host ""
Write-Host "Setup complete. Next:" -ForegroundColor Green
Write-Host "  cd backend"
Write-Host "  python -m uvicorn app.main:app --reload --port 8000"
Write-Host "Then open frontend\index.html"
