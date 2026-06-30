"""
core/logger.py — Interaction logging

Every query and response gets logged. This is required by the
project deliverables ("Logs of agent steps or sample scenarios")
and is genuinely useful for debugging and demo evidence.
"""

import sqlite3
import json
import os
from datetime import datetime
import config


def _get_connection():
    os.makedirs(os.path.dirname(config.LOG_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.LOG_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            query TEXT,
            answer TEXT,
            grounded INTEGER,
            schemes_referenced TEXT,
            backend_used TEXT,
            fallback_used INTEGER
        )
    """)
    return conn


def log_interaction(query: str, result: dict):
    conn = _get_connection()
    conn.execute(
        """
        INSERT INTO interactions
        (timestamp, query, answer, grounded, schemes_referenced, backend_used, fallback_used)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            query,
            result.get("answer", ""),
            int(result.get("grounded", False)),
            json.dumps(result.get("schemes_referenced", [])),
            result.get("backend_used") or "none",
            int(result.get("fallback_used", False)),
        ),
    )
    conn.commit()
    conn.close()


def get_recent_logs(limit: int = 20) -> list:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT timestamp, query, answer, grounded, backend_used, fallback_used "
        "FROM interactions ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
