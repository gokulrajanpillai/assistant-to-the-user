"""
ATHU Core - Memory System
Short-term: in-process conversation deque (last 20 turns).
Long-term: ChromaDB vector similarity store.
"""

from collections import deque
from datetime import datetime
import logging

logger = logging.getLogger("athu.memory")


class ConversationMemory:
    """Short-term in-process memory — last N conversation turns."""

    def __init__(self, max_turns: int = 20):
        # Each turn = user message + assistant message = 2 entries
        self._history: deque[dict] = deque(maxlen=max_turns * 2)

    def add_user(self, text: str):
        self._history.append({"role": "user", "content": text})

    def add_assistant(self, text: str):
        self._history.append({"role": "assistant", "content": text})

    def get_history(self) -> list[dict]:
        return list(self._history)

    def clear(self):
        self._history.clear()

    def __len__(self):
        return len(self._history)


class LongTermMemory:
    """ChromaDB-backed semantic long-term memory."""

    def __init__(self, persist_dir: str = "data/chroma"):
        self._client = None
        self._collection = None
        self._persist_dir = persist_dir

    def _init(self):
        if self._client is not None:
            return
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name="athu_memory",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB long-term memory initialised.")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable: {e}. Long-term memory disabled.")
            self._client = False  # Mark as failed

    def store(self, text: str, metadata: dict | None = None):
        self._init()
        if not self._client:
            return
        try:
            doc_id = f"mem_{datetime.utcnow().timestamp()}"
            self._collection.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[{**(metadata or {}), "timestamp": datetime.utcnow().isoformat()}],
            )
        except Exception as e:
            logger.error(f"Memory store error: {e}")

    def query(self, text: str, n_results: int = 3) -> list[str]:
        self._init()
        if not self._client:
            return []
        try:
            if self._collection.count() == 0:
                return []
            results = self._collection.query(query_texts=[text], n_results=n_results)
            return results["documents"][0] if results.get("documents") else []
        except Exception as e:
            logger.error(f"Memory query error: {e}")
            return []


class ATHUMemory:
    """Unified memory interface combining short-term and long-term storage."""

    def __init__(self):
        self.short_term = ConversationMemory()
        self.long_term = LongTermMemory()

    def get_context_for_query(self, query: str) -> str:
        """Retrieve semantically relevant past context for a given query."""
        relevant = self.long_term.query(query)
        if not relevant:
            return ""
        return "\n".join(f"- {doc}" for doc in relevant)

    def record_exchange(self, user_text: str, assistant_text: str, store_long_term: bool = True):
        """Record a user/assistant exchange in both memory layers."""
        self.short_term.add_user(user_text)
        self.short_term.add_assistant(assistant_text)
        if store_long_term:
            combined = f"User: {user_text}\nATHU: {assistant_text}"
            self.long_term.store(combined)

    def clear_short_term(self):
        self.short_term.clear()
