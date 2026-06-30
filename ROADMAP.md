# Jan Sahayak — Roadmap

This document separates what is **built and working** in this submission
from what is **architecturally planned** for future phases. The scoping
decisions below were made deliberately under a hard 8-day deadline, not
due to lack of ideas — every Phase 2+ item below has a clear design and
a clear reason it was deferred rather than rushed.

## Phase 1 — This Submission (Working)

- Deterministic retrieval (TF-IDF) over a manually-curated, verified
  knowledge base of central government farmer schemes
- Multi-provider LLM fallback chain: Gemini → Groq → local/lab-GPU Ollama,
  with automatic switching and visible backend reporting per answer
- Guardrail layer enforcing: grounded-in-evidence, no legal-advice
  language, mandatory next-step, length limits, and field-level
  `INFORMATION_WITHHELD` markers preventing the LLM from inventing
  missing facts
- Hindi/Hinglish/English multilingual support via keyword-bridged
  retrieval and language-aware prompting
- Full interaction logging (SQLite)
- Config-driven feature switches for every optional capability

## Phase 2 — Architecturally Scaffolded, Not Yet Built

These have real folders, real stub files with full docstrings describing
intended design, and config switches already named — but no working logic.
See the referenced files for detailed design notes.

### Automated data ingestion (`ingestion/`)
- `scraper.py` — Playwright/BeautifulSoup pipeline to pull scheme data
  directly from myscheme.gov.in and similar portals, replacing manual
  CSV curation. Deferred because robust scraping (pagination, dynamic
  rendering, site-structure resilience) is a multi-day effort that
  risks breaking under deadline pressure.
- `pdf_parser.py` — Extracts eligibility rules from linked government
  PDF guidelines using pdfplumber, with OCR fallback for scanned documents.
- `data_cleaner.py` — Validation/deduplication gate between raw scraped
  data and the trusted knowledge base, enforcing the same
  `INFORMATION_WITHHELD` discipline used in the live system today.

### State-level and hyperlocal scoping
- PIN-code-to-state routing for surfacing state-specific schemes
  alongside central ones (PIN code structurally encodes state/region,
  confirmed via official India Post documentation)
- Ward-level routing for hyperlocal municipal services — deferred
  because ward data isn't standardized nationally the way PIN codes
  are; would require state-by-state data collection
- Priority state expansion targets: Chhattisgarh, Himachal Pradesh
- Config switch: `PINCODE_ROUTING_ENABLED = False`

### Additional domains (proving "one engine, many domains")
- `domains/consumer_complaint_agent.py` — stub showing how the original
  Consumer Complaint Evidence Builder project scope plugs into the same
  core engine with zero changes to retrieval, guardrails, or LLM logic
- Public Scheme Eligibility Assistant domain (same pattern)
- Post office services and benefits domain
- Insurance claim assistance domain (aligned with NGO use case)

### Personalization layer
- Lightweight `user_context` (education/work status, immediate-need vs
  long-term-goal) collected via 2 questions at session start, used to
  weight retrieval — e.g. distinguishing a 12th-pass youth who may
  benefit more from skill-development or entrepreneurship schemes than
  manual-labor guarantee schemes
- Explicitly NOT pursuing: deep psychological/personality profiling
  tied to identity documents. This was considered and deliberately
  rejected — centralizing personality data tied to national ID creates
  real surveillance and discrimination risk regardless of intent. The
  scoped-down version (stated goals, asked once, used transiently) gets
  the same practical benefit without that risk.

### Voice interface
- Whisper (STT) + gTTS (TTS) pipeline, fully modular, toggled via a
  single `VOICE_ENABLED` switch in `config.py`
- Demonstrated as a recorded preview/teaser in the submission video
  rather than a live (and likely fragile) in-demo feature

### Trend awareness and live data
- Periodic web-search-based refresh for scheme status changes
  (deadlines, new schemes, discontinued schemes)
- Google Maps location auto-detection — considered, deferred in favor
  of explicit user-provided PIN code (more reliable, more private,
  doesn't require location permission friction)

## Design Principle Carried Through All Phases

Every Phase 2 item above is designed to slot into the existing
`core/agent_engine.py` orchestration without modification. The
deterministic-skeleton-with-LLM-at-the-edges principle — retrieval and
guardrails are pure logic, the LLM only explains what was already
verified — applies identically regardless of how many domains, languages,
or data sources are added on top of it.
