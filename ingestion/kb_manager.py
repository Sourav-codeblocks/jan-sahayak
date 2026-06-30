"""
ingestion/kb_manager.py — Controlled knowledge base ingestion

PURPOSE:
A single, safe entry point for adding or updating scheme data, so the
knowledge base never gets edited by hand in five different inconsistent
ways. Every future data source — manually researched schemes, Phase 2
scraper output, state data, anything — should pass through THIS file's
functions before landing in knowledge/farmer_schemes_kb.csv.

This is intentionally simple today (validates + appends to a CSV via
pandas) but is structured so Phase 2 ingestion sources (scraper.py,
pdf_parser.py) can call add_scheme() or bulk_ingest() directly without
needing to know anything about CSV formatting, TF-IDF rebuilding, or
the Hindi-keyword-bridge pattern — this file owns those rules.

USAGE (from a Python shell or future ingestion scripts):

    from ingestion.kb_manager import add_scheme

    add_scheme({
        "scheme_id": "PMKVY011",
        "scheme_name": "Pradhan Mantri Kaushal Vikas Yojana",
        "department": "Ministry of Skill Development and Entrepreneurship",
        "eligibility_criteria": "Youth aged 15-45 seeking skill certification",
        "land_holding_limit": "Not applicable",
        "income_limit": "No limit",
        "required_documents": "Aadhaar card, education certificates",
        "benefit_description": "Free skill training with certification and placement assistance",
        "application_process": "Register at nearest PMKVY training center or pmkvyofficial.org",
        "official_link": "https://pmkvyofficial.org",
        "hindi_keywords": "skill training, naukri ke liye training, kaushal vikas, certificate course",
    })

After calling add_scheme() or bulk_ingest(), the in-memory retriever
cache is automatically invalidated so the NEXT query picks up the new
data without needing to restart the whole application.
"""

import os
import pandas as pd
import config

REQUIRED_FIELDS = [
    "scheme_id", "scheme_name", "department", "eligibility_criteria",
    "land_holding_limit", "income_limit", "required_documents",
    "benefit_description", "application_process", "official_link",
]
OPTIONAL_FIELDS = ["hindi_keywords"]
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


class IngestionError(Exception):
    pass


def _validate_entry(entry: dict) -> dict:
    """
    Validates a single scheme entry before it's allowed into the
    knowledge base. Missing required fields are an error — this is
    deliberately strict so bad data can't silently corrupt the KB.
    Missing optional fields default to empty string.
    """
    missing = [f for f in REQUIRED_FIELDS if f not in entry or not str(entry[f]).strip()]
    if missing:
        raise IngestionError(
            f"Cannot ingest scheme '{entry.get('scheme_id', '?')}': "
            f"missing required fields {missing}"
        )

    clean_entry = {field: entry.get(field, "") for field in ALL_FIELDS}
    return clean_entry


def _check_duplicate(df: pd.DataFrame, scheme_id: str) -> bool:
    return scheme_id in df["scheme_id"].values


def add_scheme(entry: dict, allow_overwrite: bool = False) -> dict:
    """
    Adds (or optionally updates) a single scheme in the knowledge base CSV.
    Validates required fields, prevents accidental duplicates, and
    invalidates the retriever cache so changes take effect immediately.

    Returns a summary dict: {"status": "added"|"updated", "scheme_id": ...}
    """
    clean_entry = _validate_entry(entry)

    df = pd.read_csv(config.SCHEME_KB_CSV)
    is_duplicate = _check_duplicate(df, clean_entry["scheme_id"])

    if is_duplicate and not allow_overwrite:
        raise IngestionError(
            f"Scheme '{clean_entry['scheme_id']}' already exists. "
            f"Pass allow_overwrite=True to update it instead."
        )

    if is_duplicate and allow_overwrite:
        df = df[df["scheme_id"] != clean_entry["scheme_id"]]
        status = "updated"
    else:
        status = "added"

    df = pd.concat([df, pd.DataFrame([clean_entry])], ignore_index=True)
    df.to_csv(config.SCHEME_KB_CSV, index=False)

    _invalidate_retriever_cache()

    return {"status": status, "scheme_id": clean_entry["scheme_id"]}


def bulk_ingest(entries: list, allow_overwrite: bool = False) -> dict:
    """
    Ingests multiple scheme entries in one call. Stops on the first
    validation error rather than partially ingesting a bad batch —
    all-or-nothing is safer than a half-corrupted knowledge base.

    Returns {"added": [...], "updated": [...], "errors": [...]}.
    """
    results = {"added": [], "updated": [], "errors": []}

    for entry in entries:
        try:
            result = add_scheme(entry, allow_overwrite=allow_overwrite)
            results[result["status"]].append(result["scheme_id"])
        except IngestionError as e:
            results["errors"].append(str(e))

    return results


def list_all_schemes() -> list:
    """Returns scheme_id + scheme_name for every entry currently in the KB."""
    df = pd.read_csv(config.SCHEME_KB_CSV)
    return df[["scheme_id", "scheme_name"]].to_dict("records")


def remove_scheme(scheme_id: str) -> dict:
    """Removes a scheme by ID. Raises IngestionError if it doesn't exist."""
    df = pd.read_csv(config.SCHEME_KB_CSV)
    if not _check_duplicate(df, scheme_id):
        raise IngestionError(f"Scheme '{scheme_id}' not found, nothing removed.")

    df = df[df["scheme_id"] != scheme_id]
    df.to_csv(config.SCHEME_KB_CSV, index=False)
    _invalidate_retriever_cache()

    return {"status": "removed", "scheme_id": scheme_id}


def _invalidate_retriever_cache():
    """
    Forces the next retrieve() call to rebuild from the updated CSV
    instead of serving stale in-memory data. Mirrors the singleton
    pattern in core/retrieval.py.
    """
    from core import retrieval
    retrieval._retriever_instance = None
