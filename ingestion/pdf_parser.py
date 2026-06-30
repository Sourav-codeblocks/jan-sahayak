"""
ingestion/pdf_parser.py — PHASE 2 (Not implemented for capstone submission)

PURPOSE:
Many government schemes publish their full eligibility rules and
application guidelines as linked PDFs rather than structured web pages.
This module will extract and clean text from those PDFs so it can be
folded into the knowledge base alongside scraped/manually-curated data.

PLANNED IMPLEMENTATION (Phase 2):
  - pdfplumber for text + table extraction (preferred over pypdf for
    government PDFs which often contain tabular eligibility matrices)
  - OCR fallback (pytesseract) for scanned, non-text PDFs — common with
    older state government circulars
  - Output normalized into the same eligibility_criteria sub-schema used
    by ingestion/scraper.py, so downstream code (retrieval, guardrails)
    never needs to know whether a fact came from HTML or PDF

See ingestion/scraper.py for the full target schema this module's output
must conform to.
"""

raise NotImplementedError(
    "ingestion/pdf_parser.py is a Phase 2 architectural placeholder. "
    "Not used in current capstone submission."
)
