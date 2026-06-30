"""
ingestion/data_cleaner.py — PHASE 2 (Not implemented for capstone submission)

PURPOSE:
Normalizes raw output from scraper.py and pdf_parser.py into the clean,
deduplicated, validated CSV rows that core/retrieval.py expects. Acts as
the single quality gate between "raw scraped text" and "trusted knowledge
base entry."

PLANNED RESPONSIBILITIES (Phase 2):
  - Deduplicate schemes that appear across multiple source pages
  - Validate every row against the target schema (see scraper.py docstring)
  - Enforce INFORMATION_WITHHELD for any field that fails extraction
    confidence checks, rather than allowing partial/uncertain text through
  - Flag schemes whose source data conflicts across sources for human
    review before being added to the live knowledge base (never auto-merge
    conflicting facts silently)
"""

raise NotImplementedError(
    "ingestion/data_cleaner.py is a Phase 2 architectural placeholder. "
    "Not used in current capstone submission."
)
