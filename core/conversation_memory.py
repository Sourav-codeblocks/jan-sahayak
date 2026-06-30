"""
core/conversation_memory.py — Short-term, per-user conversation memory

PRINCIPLE: This is intentionally minimal — it remembers only the user's
LAST question and answer, not a full transcript. This is enough to
resolve immediate follow-ups like "??", "what about for women", "and
documents?" without building a full long-term memory system.

Stored in-memory (a plain dict), not a database — this resets if the
process restarts, which is an acceptable, honest tradeoff for "short
context window" rather than persistent chat history. If true persistent
memory is needed later, this is the single place to swap in a real store
(SQLite, Redis) without touching agent_engine.py's calling code.
"""

# user_id -> {"query": str, "answer": str}
_last_exchange = {}

MAX_USERS_TRACKED = 5000  # simple safety cap to avoid unbounded growth


def get_last_exchange(user_id) -> dict | None:
    return _last_exchange.get(user_id)


def store_exchange(user_id, query: str, answer: str):
    if len(_last_exchange) >= MAX_USERS_TRACKED and user_id not in _last_exchange:
        # Simple eviction: drop one arbitrary old entry rather than grow
        # unbounded. Fine for this scale; a real cache (LRU) would be
        # the upgrade path if this matters at higher volume.
        _last_exchange.pop(next(iter(_last_exchange)))

    _last_exchange[user_id] = {"query": query, "answer": answer}


def clear_exchange(user_id):
    _last_exchange.pop(user_id, None)
