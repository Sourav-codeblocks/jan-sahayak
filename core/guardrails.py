"""
core/guardrails.py — Deterministic rule layer

CRITICAL PRINCIPLE: This file contains ZERO calls to any LLM.
Every function here is pure Python logic. The LLM is never trusted
to enforce its own boundaries — these rules check its output instead.

This is the "nervous system" — fast, predictable, never hallucinates
because it isn't generating anything, only checking and routing.
"""

import re
import config


class GuardrailViolation(Exception):
    """Raised when an agent response fails a hard guardrail check."""
    pass


def check_grounded_in_evidence(response_text: str, retrieved_docs: list) -> bool:
    """
    Returns False if the response makes claims with no supporting
    retrieved document. This is a simple keyword-overlap check —
    not perfect, but catches obvious hallucination/no-evidence cases.
    """
    if not retrieved_docs:
        return False

    combined_evidence = " ".join(
        [doc.get("text", "") for doc in retrieved_docs]
    ).lower()

    # Pull out scheme names mentioned in the response
    scheme_mentions = re.findall(r"[A-Z][a-zA-Z\-]{3,}(?:\s[A-Z][a-zA-Z\-]{3,}){0,3}", response_text)

    if not scheme_mentions:
        # No specific scheme claims made — nothing risky to verify
        return True

    for mention in scheme_mentions:
        if mention.lower()[:6] in combined_evidence:
            return True

    return False


def check_no_legal_advice(response_text: str) -> bool:
    """
    Blocks language that sounds like a legal guarantee or verdict.
    The agent must describe eligibility criteria and next steps,
    never promise outcomes.
    """
    banned_phrases = [
        "you will definitely get",
        "guaranteed approval",
        "you will win",
        "100% eligible",
        "legally entitled to receive",
    ]
    lowered = response_text.lower()
    return not any(phrase in lowered for phrase in banned_phrases)


def check_has_next_step(response_text: str) -> bool:
    """
    Every response must end with something actionable.
    Checks for: an explicit "Next Step" header (any case/language),
    or action-indicating keywords near the end — in Roman script,
    Hinglish, AND Devanagari Hindi script.
    """
    # Explicit header check first — most reliable signal
    if re.search(r"next\s*step", response_text, re.IGNORECASE):
        return True

    action_keywords = [
        # English / Hinglish (Roman script)
        "visit", "submit", "contact", "apply", "bring", "carry",
        "register", "call", "agla kadam", "sampark", "jama karein",
        "ja sakte", "milna", "office", "documents", "aavedan",
        # Devanagari Hindi script
        "अगला कदम", "संपर्क", "आवेदन", "जाएं", "जाकर", "कार्यालय",
        "दस्तावेज़", "जमा करें", "विज़िट",
    ]
    tail = response_text[-400:].lower()
    return any(keyword.lower() in tail for keyword in action_keywords)


def check_length(response_text: str) -> bool:
    """Keeps responses focused — long answers reduce trust and clarity."""
    word_count = len(response_text.split())
    return word_count <= config.MAX_RESPONSE_WORDS


def run_all_guardrails(response_text: str, retrieved_docs: list) -> dict:
    """
    Master guardrail runner. Returns a structured result so the
    agent_engine can decide whether to send the response, retry,
    or fall back to the safe "no data" message.
    """
    results = {
        "grounded": check_grounded_in_evidence(response_text, retrieved_docs),
        "no_legal_advice": check_no_legal_advice(response_text),
        "has_next_step": check_has_next_step(response_text),
        "within_length": check_length(response_text),
    }
    results["passed"] = all(results.values())

    import config
    if config.DEMO_MODE and not results["passed"]:
        failed_checks = [k for k, v in results.items() if k != "passed" and not v]
        print(f"[guardrails] Response REJECTED. Failed checks: {failed_checks}")
        print(f"[guardrails] RAW TEXT THAT WAS REJECTED:\n{response_text}\n---END RAW TEXT---")

    return results


def get_safe_fallback(language: str = "hi") -> str:
    """Returns the hardcoded safe message when guardrails fail."""
    return config.FALLBACK_NO_DATA_MESSAGE.get(
        language, config.FALLBACK_NO_DATA_MESSAGE["en"]
    )
