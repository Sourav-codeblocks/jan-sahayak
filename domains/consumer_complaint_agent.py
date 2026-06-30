"""
domains/consumer_complaint_agent.py — PHASE 2 (Not implemented for capstone submission)

PURPOSE:
Demonstrates that Jan Sahayak's core engine (core/agent_engine.py) is
domain-agnostic by design. This file exists to show HOW a second domain
plugs into the existing architecture with zero changes to the core engine,
retrieval logic, or guardrails — only a new knowledge base CSV and a thin
wrapper are needed.

This mirrors the original capstone project scope (Consumer Complaint
Evidence Builder Agent) and proves the "one engine, many domains" thesis
described in the project report.

TO ACTIVATE THIS DOMAIN (Phase 2):
    1. Populate knowledge/consumer_complaints_kb.csv with real complaint
       category data (see knowledge/farmer_schemes_kb.csv for the proven
       CSV shape and Hindi-keyword-bridge pattern to follow)
    2. Point config.SCHEME_KB_CSV at the new file, OR extend
       core/retrieval.py to support multiple named knowledge bases
       selected by domain
    3. No changes needed to core/agent_engine.py, core/guardrails.py,
       or core/llm_connector.py — the deterministic-skeleton-with-LLM-
       at-the-edges principle applies identically across domains
"""

from core import agent_engine


def handle_consumer_query(query: str, language: str = "hi") -> dict:
    """
    Placeholder entry point. Once the consumer complaints knowledge base
    (knowledge/consumer_complaints_kb.csv) is populated, this becomes a
    one-line wrapper around agent_engine.handle_query(), exactly like
    the farmer subsidy domain.
    """
    raise NotImplementedError(
        "Consumer complaint domain is a Phase 2 architectural placeholder. "
        "Knowledge base not yet populated. See module docstring."
    )
