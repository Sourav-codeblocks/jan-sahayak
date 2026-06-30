"""
core/llm_connector.py — Multi-provider LLM abstraction with auto-switching

PRINCIPLE: agent_engine never talks to a specific provider directly.
It calls generate(prompt) here. This module tries providers in the
order defined by config.LLM_PROVIDER_ORDER, and reports back exactly
which one answered — so every response can show its provenance
(useful for demos, debugging, and proving "zero hallucination, real
fallback chain" to evaluators).

Switching logic:
  1. Try each provider in config.LLM_PROVIDER_ORDER, in sequence
  2. First one that succeeds wins — its name and latency are returned
  3. If a provider has no API key configured, it's skipped silently
     (no wasted network call)
  4. If ALL providers fail -> raise LLMError; agent_engine handles
     this with the guardrail fallback message, never a silent crash
"""

import time
import requests
import config


class LLMError(Exception):
    pass


def _call_gemini(prompt: str) -> str:
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning, module="google")
    import google.generativeai as genai

    if not config.GEMINI_API_KEY:
        raise LLMError("No Gemini API key configured")

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL)
    response = model.generate_content(prompt)
    return response.text.strip()


def _call_groq(prompt: str) -> str:
    if not config.GROQ_API_KEY:
        raise LLMError("No Groq API key configured")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post(
        url, headers=headers, json=payload, timeout=config.LLM_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _call_ollama(prompt: str) -> str:
    url = f"{config.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["response"].strip()


_PROVIDER_FUNCTIONS = {
    "gemini": _call_gemini,
    "groq": _call_groq,
    "ollama": _call_ollama,
}


def generate(prompt: str) -> dict:
    """
    Returns {"text": ..., "backend_used": "gemini" | "groq" | "ollama",
    "latency_seconds": float}.
    Tries providers in config.LLM_PROVIDER_ORDER, falls back automatically,
    raises LLMError only if every provider fails.
    """
    last_error = None

    for provider_name in config.LLM_PROVIDER_ORDER:
        call_fn = _PROVIDER_FUNCTIONS.get(provider_name)
        if call_fn is None:
            continue
        try:
            start = time.time()
            text = call_fn(prompt)
            elapsed = time.time() - start
            return {
                "text": text,
                "backend_used": provider_name,
                "latency_seconds": round(elapsed, 2),
            }
        except Exception as e:
            last_error = e
            if config.DEMO_MODE:
                short_reason = _summarize_error(e)
                print(f"[llm_connector] {provider_name} unavailable ({short_reason}) — trying next provider...")
            continue

    raise LLMError(f"All LLM providers failed. Last error: {last_error}")


def _summarize_error(e: Exception) -> str:
    """
    Reduces a verbose provider exception (often containing multi-line
    quota/violation JSON dumps) into a short, readable one-liner for
    terminal/demo output. Falls back to the first line of the error
    if no known pattern is detected.
    """
    text = str(e)

    if "429" in text or "quota" in text.lower():
        return "rate limit / quota exceeded"
    if "Connection refused" in text or "ConnectionError" in text:
        return "connection refused (service not running or unreachable)"
    if "timeout" in text.lower():
        return "request timed out"
    if "401" in text or "authentication" in text.lower() or "API key" in text:
        return "authentication failed (check API key)"

    # Fallback: just the first line, truncated
    first_line = text.strip().split("\n")[0]
    return first_line[:100]
