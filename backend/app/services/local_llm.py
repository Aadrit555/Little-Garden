"""
Local LLM client — talks to Ollama running on localhost. No external
API, no cloud call, no data ever leaves the machine this runs on.

Ollama serves an OpenAI-style REST API at http://localhost:11434 once
you run `ollama serve` (or it auto-starts on install). Model must be
pulled once: `ollama pull llama3.1:8b-instruct-q4_K_M` (fits a 6GB GPU
like an RTX 3050 in 4-bit quantization — real constraint, chosen for it).

This is a real HTTP call to a real local process — not a mock. If
Ollama isn't running or the model isn't pulled, this raises a real
connection error, and callers (writing_grader, reading_grader,
listening_service) surface that as a real pipeline error — no silent
fallback score.
"""
import os
import json
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.environ.get("LOCAL_LLM_MODEL")


def _resolve_model_name() -> str:
    if MODEL_NAME:
        return MODEL_NAME
    try:
        response = requests.get(OLLAMA_URL.rsplit("/", 1)[0] + "/tags", timeout=5)
        response.raise_for_status()
        models = [item.get("name") for item in response.json().get("models", []) if item.get("name")]
    except requests.RequestException as exc:
        raise RuntimeError("Could not inspect local Ollama models. Set LOCAL_LLM_MODEL or start Ollama.") from exc
    if not models:
        raise RuntimeError("No local Ollama model is installed. Set LOCAL_LLM_MODEL after pulling a model.")
    if len(models) > 1:
        raise RuntimeError(f"Multiple Ollama models installed. Set LOCAL_LLM_MODEL explicitly: {models}")
    return models[0]


def local_llm_json_call(system: str, messages: list[dict], max_tokens: int = 800) -> dict:
    """
    Calls the local Ollama server, expects the model to return raw JSON
    (per system prompt instructions). Parses and returns it. Raises on
    any failure — connection refused, bad JSON, timeout — real errors,
    not faked results.
    """
    model_name = _resolve_model_name()
    payload = {
        "model": model_name,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "format": "json",   # Ollama's structured-output mode — forces valid JSON
        "options": {"temperature": 0.2},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            "Could not reach local Ollama server at "
            f"{OLLAMA_URL}. Is `ollama serve` running and is "
            f"'{model_name}' pulled? (`ollama pull {model_name}`)"
        ) from e

    resp.raise_for_status()
    body = resp.json()
    raw_content = body.get("message", {}).get("content", "")

    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Local model returned non-JSON output: {raw_content[:200]}") from e

    return result
