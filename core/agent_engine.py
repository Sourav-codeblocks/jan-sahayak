"""
core/agent_engine.py — The orchestrator (the "brain")

Flow for every query:
  0. Deterministic smalltalk gate (greetings/identity/thanks/unclear)
  1. Retrieve relevant scheme documents (deterministic, Layer 1)
  2. If nothing relevant found -> return safe fallback immediately,
     never call the LLM to "guess"
  3. If relevant docs found -> build a grounded prompt and call LLM
     to explain ONLY what was retrieved
  4. Run guardrails on the LLM output
  5. If guardrails fail -> return safe fallback (never the raw LLM text)
  6. If guardrails pass -> return structured, logged response

This is the deterministic skeleton + LLM at the edges principle in code.
"""

import config
from core import retrieval, llm_connector, guardrails, logger, conversation_memory

import json as _json
import re as _re

# ---------------------------------------------------------------------
# SMALLTALK GATE — deterministic, runs BEFORE retrieval.
# Patterns and replies live in knowledge/smalltalk.json (data, not code),
# same philosophy as the scheme KB. If the file is missing, the gate
# quietly disables itself rather than crashing the bot.
# ---------------------------------------------------------------------
try:
    with open("./knowledge/smalltalk.json", encoding="utf-8") as _f:
        SMALLTALK = _json.load(_f)
except (FileNotFoundError, _json.JSONDecodeError):
    SMALLTALK = []

UNCLEAR_REPLY = {
    "hi": "Maaf kijiye, main samajh nahi paaya. Aise poochhiye — 'PM Kisan kya hai?' ya 'fasal bima kaise milega?'",
    "en": "Sorry, I didn't catch that. Try: 'What is PM Kisan?' or 'How do I get crop insurance?'",
}


def check_smalltalk(query, lang):
    """Returns a canned reply if query is smalltalk/unclear, else None."""
    q = query.strip().lower()
    # Gibberish / too short to be a real question
    if len(_re.sub(r"[^a-z\u0900-\u097F]", "", q)) < 3:
        return UNCLEAR_REPLY.get(lang, UNCLEAR_REPLY["en"])
    for entry in SMALLTALK:
        for p in entry["patterns"]:
            if _re.search(p, q):
                return entry.get(lang, entry["en"])
    return None


PROMPT_TEMPLATE = """You are Sprout, a helpful assistant for Indian farmers. If a user asks who you are, describe yourself as Sprout, the guide - Sprout is your only name.
A farmer has asked a question. Below are the ONLY verified government scheme
documents you may use to answer. Do not invent any scheme, amount, or rule
that is not in these documents.
{previous_context}
VERIFIED SCHEME DOCUMENTS:
{evidence}

FARMER'S QUESTION:
{query}

INSTRUCTIONS:
- Answer in {language_name}, in simple, warm, respectful language a farmer would understand.
- Only mention schemes and facts present in the documents above.
- If the farmer's question is short, vague, or seems like a follow-up (e.g. "??",
  "and for women?", "what documents?"), use the PREVIOUS EXCHANGE above (if any)
  to understand what they're really asking about, and answer that follow-up
  specifically rather than giving a generic response.
- If any field in the documents above shows the exact text "INFORMATION_WITHHELD",
  this means that specific detail is not verified. Do NOT state, estimate, or guess
  a value for it. Instead say that detail isn't confirmed and the farmer should ask
  at the local office.
- If multiple schemes are provided above, identify the ONE most relevant to the
  farmer's question and focus your answer on that scheme only. Do not list or
  explain every scheme provided — pick the best match.
- Keep the answer under {max_words} words. Be concise — a farmer reading this on
  a phone screen needs the key facts quickly, not an exhaustive explanation.
- ALWAYS end with a clear "Next Step" telling the farmer exactly what to do
  (which office to visit, which documents to carry, or which portal to use).
- Do not promise approval or guarantee outcomes. Describe eligibility criteria,
  not verdicts.
"""

LANGUAGE_NAMES = {
    "hi": "Hindi",
    "en": "English",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
}


def handle_query(query: str, language: str = None, user_id=None) -> dict:
    """
    Main entry point. Returns a structured response dict:
    {
        "answer": str,
        "grounded": bool,
        "schemes_referenced": [...],
        "backend_used": str or None,
        "guardrail_results": {...} or None,
        "fallback_used": bool,
    }

    If user_id is provided, the system remembers this user's last
    question/answer and uses it to resolve short follow-up queries
    (e.g. "??", "and for women?"). See core/conversation_memory.py.
    """
    language = language or config.LANGUAGE_DEFAULT
    language_name = LANGUAGE_NAMES.get(language, "English")

    previous = conversation_memory.get_last_exchange(user_id) if user_id else None

    # Step 0 — Deterministic smalltalk gate (greetings/identity/thanks).
    # Short/unclear queries only count as "unclear" when there's no
    # conversation history — with history they're follow-ups, handled below.
    smalltalk_reply = check_smalltalk(query, language)
    if smalltalk_reply and not (previous and len(query.strip()) <= 6):
        return {
            "answer": smalltalk_reply,
            "grounded": True,
            "schemes_referenced": [],
            "backend_used": "smalltalk",
            "guardrail_results": None,
            "fallback_used": False,
        }

    # If the current query is very short, it's likely a follow-up rather
    # than a standalone question — widen retrieval by searching against
    # the PREVIOUS question too, so retrieval doesn't fail just because
    # "??" alone matches nothing in the knowledge base.
    retrieval_query = query
    if previous and len(query.strip()) <= 6:
        retrieval_query = previous["query"] + " " + query

    # Step 1 — Deterministic retrieval, no LLM involved
    retriever = retrieval.get_retriever()
    retrieved_docs = retriever.retrieve(retrieval_query)

    relevant_docs = [
        d for d in retrieved_docs if d.get("score", 0) >= config.RAG_MIN_RELEVANCE
    ]

    # Step 2 — No relevant evidence -> safe fallback, LLM never called
    if not relevant_docs:
        fallback_text = guardrails.get_safe_fallback(language)
        result = {
            "answer": fallback_text,
            "grounded": False,
            "schemes_referenced": [],
            "backend_used": None,
            "guardrail_results": None,
            "fallback_used": True,
        }
        logger.log_interaction(query, result)
        return result

    # Step 3 — Build grounded prompt and call LLM
    evidence_text = "\n\n".join([d["text"] for d in relevant_docs])
    previous_context = ""
    if previous:
        previous_context = (
            f"\nPREVIOUS EXCHANGE (for context only — answer the CURRENT question, "
            f"using this only to understand follow-ups):\n"
            f"Previous question: {previous['query']}\n"
            f"Previous answer: {previous['answer']}\n"
        )
    prompt = PROMPT_TEMPLATE.format(
        previous_context=previous_context,
        evidence=evidence_text,
        query=query,
        language_name=language_name,
        max_words=config.MAX_RESPONSE_WORDS,
    )

    try:
        llm_result = llm_connector.generate(prompt)
        raw_answer = llm_result["text"]
        backend_used = llm_result["backend_used"]
    except llm_connector.LLMError:
        fallback_text = guardrails.get_safe_fallback(language)
        result = {
            "answer": fallback_text,
            "grounded": False,
            "schemes_referenced": [],
            "backend_used": None,
            "guardrail_results": None,
            "fallback_used": True,
        }
        logger.log_interaction(query, result)
        return result

    # Step 4 — Guardrail check on LLM output
    guardrail_results = guardrails.run_all_guardrails(raw_answer, relevant_docs)

    # Step 5 — Fail closed: if guardrails fail, never show raw LLM text
    if not guardrail_results["passed"]:
        fallback_text = guardrails.get_safe_fallback(language)
        result = {
            "answer": fallback_text,
            "grounded": False,
            "schemes_referenced": [d["metadata"]["scheme_name"] for d in relevant_docs],
            "backend_used": backend_used,
            "guardrail_results": guardrail_results,
            "fallback_used": True,
        }
        logger.log_interaction(query, result)
        return result

    # Step 6 — Success path
    result = {
        "answer": raw_answer,
        "grounded": True,
        "schemes_referenced": [d["metadata"]["scheme_name"] for d in relevant_docs],
        "backend_used": backend_used,
        "guardrail_results": guardrail_results,
        "fallback_used": False,
    }
    logger.log_interaction(query, result)

    if user_id:
        conversation_memory.store_exchange(user_id, query, raw_answer)

    return result
