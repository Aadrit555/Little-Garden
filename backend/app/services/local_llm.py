"""
LLM client for learner-content generation.

Production can use Gemini through the Google GenAI SDK, while local development
can continue using Ollama. The caller-facing function stays the same so the
reading/writing generation pipeline does not need to know which provider is used.
"""
import json
import os

import requests

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").strip().lower()

# Ollama settings (used when LLM_PROVIDER=ollama)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.environ.get("LOCAL_LLM_MODEL")

# Gemini settings (used when LLM_PROVIDER=gemini)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")


def _resolve_ollama_model_name() -> str:
    if MODEL_NAME:
        return MODEL_NAME
    try:
        response = requests.get(OLLAMA_URL.rsplit("/", 1)[0] + "/tags", timeout=5)
        response.raise_for_status()
        models = [
            item.get("name")
            for item in response.json().get("models", [])
            if item.get("name")
        ]
    except requests.RequestException as exc:
        raise RuntimeError(
            "Could not inspect local Ollama models. Set LOCAL_LLM_MODEL or start Ollama."
        ) from exc
    if not models:
        raise RuntimeError(
            "No local Ollama model is installed. Set LOCAL_LLM_MODEL after pulling a model."
        )
    if len(models) > 1:
        raise RuntimeError(
            f"Multiple Ollama models installed. Set LOCAL_LLM_MODEL explicitly: {models}"
        )
    return models[0]


def _ollama_json_call(system: str, messages: list[dict], max_tokens: int) -> dict:
    model_name = _resolve_ollama_model_name()
    payload = {
        "model": model_name,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2, "num_predict": max_tokens},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Could not reach local Ollama server at "
            f"{OLLAMA_URL}. Is `ollama serve` running and is "
            f"'{model_name}' pulled? (`ollama pull {model_name}`)"
        ) from exc

    resp.raise_for_status()
    body = resp.json()
    raw_content = body.get("message", {}).get("content", "")
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Local model returned non-JSON output: {raw_content[:200]}"
        ) from exc


def _gemini_json_call(system: str, messages: list[dict], max_tokens: int) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Add it to the production environment."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Gemini support is not installed. Add google-genai to backend requirements."
        ) from exc

    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = [
        types.Content(
            role=message.get("role", "user"),
            parts=[types.Part.from_text(text=message.get("content", ""))],
        )
        for message in messages
    ]

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=max_tokens,
            ),
        )
    except Exception as exc:
        raise RuntimeError(
            f"Gemini generation failed using model '{GEMINI_MODEL}': {exc}"
        ) from exc

    raw_content = (response.text or "").strip()
    if not raw_content:
        raise RuntimeError("Gemini returned an empty response")

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Gemini returned non-JSON output: {raw_content[:200]}"
        ) from exc


def local_llm_json_call(system: str, messages: list[dict], max_tokens: int = 800) -> dict:
    """
    Generate structured JSON through the configured provider.

    LLM_PROVIDER=ollama keeps the existing local-development path.
    LLM_PROVIDER=gemini uses the cloud Gemini API and is suitable for Render.
    """
    if LLM_PROVIDER == "gemini":
        return _gemini_json_call(system, messages, max_tokens)
    if LLM_PROVIDER == "ollama":
        return _ollama_json_call(system, messages, max_tokens)
    raise RuntimeError(
        f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. Use 'ollama' or 'gemini'."
    )
