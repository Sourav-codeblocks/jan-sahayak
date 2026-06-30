# Jan Sahayak — Apka Haq, Apki Bhasha

An AI agent that helps Indian farmers discover and understand government
schemes they're entitled to — in their own language, grounded entirely
in verified scheme data, with zero tolerance for hallucinated facts.

## The Problem

Millions of farmers miss out on government schemes they qualify for —
not because the schemes don't exist, but because navigating scattered
government portals, dense eligibility rules, and English-heavy
documentation is a genuine barrier. Jan Sahayak closes that gap.

## Core Design Principle

**Deterministic skeleton, LLM only at the edges.** The system never lets
an LLM invent facts about eligibility, amounts, or documents. Every
claim in a response is grounded in a retrieved, verified scheme
document. If nothing relevant is found, the system says so honestly
rather than guessing — see `core/guardrails.py`.

```
User Query
    ↓
[DETERMINISTIC] Language detection
    ↓
[DETERMINISTIC] Retrieval (TF-IDF) over verified knowledge base
    ↓
    No match? → Safe fallback message (LLM never called)
    ↓
[LLM] Explain ONLY the retrieved facts, in the user's language
    ↓
[DETERMINISTIC] Guardrail check (grounded? has next step? not too long?)
    ↓
    Fails? → Safe fallback message (raw LLM text never shown)
    ↓
Structured, trustworthy answer
```

## Architecture

| Component | Purpose |
|---|---|
| `core/retrieval.py` | TF-IDF retrieval over the knowledge base — fast, free, fully offline |
| `core/llm_connector.py` | Multi-provider LLM fallback chain (Gemini → Groq → local Ollama) |
| `core/guardrails.py` | Pure deterministic checks; zero LLM calls |
| `core/language_detect.py` | Script-based detection (Hindi, English; Tamil/Telugu detection in progress) |
| `core/agent_engine.py` | Orchestrates the full flow above |
| `ingestion/kb_manager.py` | Single safe entry point for adding/updating scheme data |
| `tools/telegram_bot.py` | Telegram interface (text + voice-ready) |
| `knowledge/farmer_schemes_kb.csv` | 10 verified central government schemes |

## Why This Architecture, Not Just "Ask an LLM"

A general AI assistant requires an account, often a subscription, and
comfort navigating a chat interface — barriers a rural farmer often
faces. Jan Sahayak is free, narrow, and accountable: every answer is
traceable to a specific verified document, never a plausible-sounding
guess. See `ROADMAP.md` for the full reasoning and what's planned next.

## Tech Stack

Python · Gemini API · Groq API · Ollama (local/lab GPU fallback) ·
scikit-learn (TF-IDF) · python-telegram-bot · pandas

Entirely free-tier capable: no required paid service for the core
experience.

## Running Locally

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
python3 tools/telegram_bot.py
```

## Deployment

Configured for Render's free tier (`render.yaml`) using webhook mode,
since Render's free tier supports Web Services but not Background
Workers. See `ROADMAP.md` for the full deployment story.

## Status

Built for the Himshikhar Track Agentic AI Capstone Project, July 2026.
See `ROADMAP.md` for what's built versus architecturally planned.
