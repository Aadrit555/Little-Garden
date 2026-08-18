#!/usr/bin/env bash
# Real one-command setup for running the German MVP directly on
# Mac/Linux (no Docker). Same real steps as setup.ps1.
set -e

echo "== German MVP setup =="

if ! command -v conda >/dev/null 2>&1; then
    echo "conda not found."
    echo "Install Miniforge first (one-time, real manual step):"
    echo "  https://github.com/conda-forge/miniforge#download"
    echo "Then re-run this script."
    exit 1
fi

echo "Installing Montreal Forced Aligner (real, via conda-forge)..."
conda install -y -c conda-forge montreal-forced-aligner

echo "Downloading real German acoustic model + dictionary..."
mfa model download acoustic german_mfa
mfa model download dictionary german_mfa

echo "Installing backend Python dependencies..."
pip install -r backend/requirements.txt

if ! command -v ollama >/dev/null 2>&1; then
    echo ""
    echo "Ollama not found — install from https://ollama.com, then run:"
    echo "  ollama pull llama3.1:8b-instruct-q4_K_M"
else
    echo "Ollama found. Checking model is pulled..."
    ollama pull llama3.1:8b-instruct-q4_K_M
fi

echo ""
echo "Setup complete. Next:"
echo "  cd backend"
echo "  python -m uvicorn app.main:app --reload --port 8000"
echo "Then open frontend/index.html"
