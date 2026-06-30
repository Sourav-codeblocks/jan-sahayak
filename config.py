"""
config.py — Jan Sahayak master control panel

Every feature in this system is a switch here.
Flip True/False to turn modules on or off without touching their code.
This is the ONLY file you should need to edit to change system behavior.
"""

import os

# Auto-load .env file if present (keeps secrets out of terminal history
# and out of code; persists across sessions without re-exporting)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed yet — fall back to shell-exported vars

# ---------------------------------------------------------------------
# FEATURE SWITCHES
# ---------------------------------------------------------------------

VOICE_ENABLED = False          # Speech-to-text + text-to-speech pipeline
SCRAPER_ENABLED = False        # Live web scraping fallback (Layer 2)
WEB_SEARCH_ENABLED = False     # Search API fallback (Layer 3)
DEMO_MODE = True               # Adds extra logging/visibility for demos

# ---------------------------------------------------------------------
# LLM CONFIGURATION — Multi-provider fallback chain
# ---------------------------------------------------------------------
# Order matters: tried left to right until one succeeds.
# Every response reports which backend actually answered (see
# agent_engine.py -> result["backend_used"]), so you always know
# whether Gemini, Groq, or your local/lab Ollama produced the answer.

LLM_PROVIDER_ORDER = ["gemini", "groq", "ollama"]

# --- Gemini ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"   # 2.0-flash is deprecated as of Mar 2026

# --- Groq (very fast inference, generous free tier, good fallback) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"

# --- Ollama (local or lab GPU via SSH tunnel) ---
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

# --- Telegram Bot ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Timeout before falling back to the next provider in the chain (seconds)
LLM_TIMEOUT_SECONDS = 15

# ---------------------------------------------------------------------
# LANGUAGE
# ---------------------------------------------------------------------

LANGUAGE_DEFAULT = "hi"        # Hindi default; auto-detected per query
SUPPORTED_LANGUAGES = ["hi", "en", "mr", "ta", "te", "bn", "gu", "pa"]

# ---------------------------------------------------------------------
# KNOWLEDGE BASE / RAG
# ---------------------------------------------------------------------

CHROMA_PERSIST_DIR = "./data/chroma_store"
SCHEME_KB_CSV = "./knowledge/farmer_schemes_kb.csv"
RAG_TOP_K = 4                  # number of documents retrieved per query
RAG_MIN_RELEVANCE = 0.04       # TF-IDF cosine score; below this, treat as "not found"
                                # NOTE: tuned low because Hindi/Hinglish colloquial
                                # queries share little vocabulary with English scheme
                                # docs. Add Hindi keyword variants to the CSV over time
                                # to allow raising this threshold safely.

# ---------------------------------------------------------------------
# GUARDRAILS
# ---------------------------------------------------------------------

FALLBACK_NO_DATA_MESSAGE = {
    "hi": "Maaf kijiye, mujhe iski pakki jaankari nahi hai. Apne block ya krishi vibhag office se sampark karein.",
    "en": "Sorry, I don't have verified information on this. Please contact your local agriculture office.",
    "ta": "மன்னிக்கவும், இதற்கான உறுதியான தகவல் என்னிடம் இல்லை. உங்கள் வட்டார வேளாண்மை அலுவலகத்தைத் தொடர்பு கொள்ளவும்.",
    "te": "క్షమించండి, దీని గురించి నాకు ధృవీకరించబడిన సమాచారం లేదు. దయచేసి మీ స్థానిక వ్యవసాయ కార్యాలయాన్ని సంప్రదించండి.",
}
# NOTE: Full retrieval support (matching Tamil/Telugu queries against the
# knowledge base) is NOT yet implemented — only Hindi and English have
# keyword-bridged retrieval today. A Tamil/Telugu query will currently
# fall through to this safe fallback message rather than finding a real
# scheme match. See ROADMAP.md "Full multilingual retrieval" for the
# planned fix: per-language keyword columns in the CSV, same pattern as
# the existing hindi_keywords column.

MAX_RESPONSE_WORDS = 220        # keeps answers focused and actionable

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

LOG_DB_PATH = "./data/logs.db"
