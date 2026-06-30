"""
ingestion/scraper.py — PHASE 2 (Not implemented for capstone submission)

PURPOSE:
Automated, rate-limited scraper for pulling scheme data directly from
official government portals (e.g. myscheme.gov.in), replacing today's
manually-curated CSV knowledge base with a continuously-refreshed one.

WHY NOT BUILT NOW:
Robust scraping (handling pagination, dynamic JS rendering, site structure
changes, and government server etiquette) is a multi-day engineering effort
on its own. For the capstone deadline, knowledge is manually curated from
verified official sources into knowledge/*.csv — accurate, but static.
This file documents the intended Phase 2 architecture so the system is
ready to absorb a real ingestion pipeline without redesigning the core
agent engine, retrieval layer, or guardrails.

TARGET SCHEMA (every scraped record will conform to this shape before
being written into the knowledge base, matching the existing CSV columns
plus structured eligibility sub-fields for finer-grained guardrail checks):

    {
        "scheme_id": str,
        "title": str,
        "ministry": str,
        "governance_level": "Central" | "State",
        "state_tag": str | "None",
        "domain": str,                  # e.g. "Agriculture", "Forestry"
        "eligibility_criteria": {
            "age_limit": str,
            "land_holding": str,
            "income_cap": str,
            "raw_rules": str,
        },
        "benefits_offered": str,
        "application_process": str,
        "required_documents": list[str],
        "source_url": str,
    }

PLANNED IMPLEMENTATION (Phase 2):
  - Playwright for JS-rendered pages, BeautifulSoup for static HTML
  - 2-3 second deterministic delay between requests (server etiquette)
  - Realistic headers, pagination handling
  - Strict rule: any field that cannot be confidently extracted is written
    as "INFORMATION_WITHHELD", never a guessed placeholder — same
    zero-hallucination principle already enforced in core/retrieval.py
  - Output written to knowledge/*.csv, hot-reloadable by the existing
    SchemeRetriever with no changes to core/agent_engine.py

CONFIG SWITCH (see config.py):
    SCRAPER_ENABLED = False   # flip True once this module is implemented
"""

raise NotImplementedError(
    "ingestion/scraper.py is a Phase 2 architectural placeholder. "
    "See module docstring for planned design. Not used in current "
    "capstone submission — knowledge base is manually curated."
)
