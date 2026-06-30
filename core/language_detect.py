"""
core/language_detect.py — Automatic input language detection

Detects which language a user's message is written in, so the system
can respond in that same language instead of always defaulting to
Hindi or requiring the caller to specify a language manually.

Uses Unicode script detection as the primary signal (fast, deterministic,
zero external calls) since Indian languages mostly use distinct scripts.
Falls back to langdetect (statistical) for cases where script alone
isn't decisive — e.g. distinguishing Hindi from Marathi, both written
in Devanagari script.
"""

import re
import config

# Unicode block ranges for distinct Indian scripts. Script alone is a
# strong, instant signal for languages that don't share a script.
SCRIPT_RANGES = {
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "te": (0x0C00, 0x0C7F),  # Telugu
    "bn": (0x0980, 0x09FF),  # Bengali
    "gu": (0x0A80, 0x0AFF),  # Gujarati
    "pa": (0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
    # Devanagari (0x0900-0x097F) is shared by Hindi and Marathi —
    # script alone can't distinguish them, handled separately below.
}

DEVANAGARI_RANGE = (0x0900, 0x097F)


def _script_of_char(char: str) -> str | None:
    code = ord(char)
    for lang, (start, end) in SCRIPT_RANGES.items():
        if start <= code <= end:
            return lang
    if DEVANAGARI_RANGE[0] <= code <= DEVANAGARI_RANGE[1]:
        return "devanagari"
    return None


def detect_language(text: str) -> str:
    """
    Returns a language code from config.SUPPORTED_LANGUAGES.
    Falls back to config.LANGUAGE_DEFAULT if detection is inconclusive
    (e.g. very short text, or text in an unsupported language/script).
    """
    script_votes = {}
    for char in text:
        script = _script_of_char(char)
        if script:
            script_votes[script] = script_votes.get(script, 0) + 1

    if not script_votes:
        # No distinctive Indian script detected — likely Latin script,
        # meaning English or Hinglish. Hinglish (Romanized Hindi) is
        # extremely common in real usage and is treated as Hindi for
        # retrieval purposes, since the hindi_keywords column already
        # contains Romanized terms.
        return _detect_latin_script(text)

    top_script = max(script_votes, key=script_votes.get)

    if top_script == "devanagari":
        # Hindi and Marathi share Devanagari script. Without deeper
        # NLP, default to Hindi — it's the more common case for this
        # system's expected user base, and Marathi can be explicitly
        # requested in future once Marathi keyword data exists.
        return "hi"

    if top_script in config.SUPPORTED_LANGUAGES:
        return top_script

    return config.LANGUAGE_DEFAULT


def _detect_latin_script(text: str) -> str:
    """
    For Latin-script text, distinguishes likely-English from likely-
    Hinglish using a small marker-word heuristic, since both use the
    same script and full statistical language detection is overkill
    for short farmer queries.
    """
    hinglish_markers = [
        "kya", "hai", "nahi", "mujhe", "kaise", "chahiye", "paisa",
        "kab", "kaha", "milega", "karna", "karein", "yojana", "yojna",
    ]
    lowered = text.lower()
    hinglish_hits = sum(1 for marker in hinglish_markers if marker in lowered)

    return "hi" if hinglish_hits >= 1 else "en"
