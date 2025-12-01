"""Shared embedding service abstractions."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..config import config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Thin wrapper around Gemini embeddings for consistent usage with caching."""

    # Class-level cache shared across all instances
    _query_cache: dict[str, tuple] = {}
    _cache_max_size: int = 128

    def __init__(self, model_name: str = "gemini-embedding-001", api_key: Optional[str] = None) -> None:
        self.model_name = model_name
        self._api_key = api_key or config.llm.effective_api_key
        self._ensure_event_loop()
        self._embedding_client = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=self._api_key,
        )

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single document-sized text snippet."""
        embedding = self._embedding_client.embed_documents([text])[0]
        return np.array(embedding, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a user query for similarity search with caching.

        Uses a class-level cache to avoid repeated API calls for the same query.
        Cache hit saves ~100-150ms per query.
        """
        # Normalize query for better cache hits
        cache_key = query.lower().strip()

        # Check cache first
        if cache_key in self._query_cache:
            logger.debug(f"⚡ Embedding cache HIT for query: '{query[:40]}...'")
            return np.array(self._query_cache[cache_key], dtype=np.float32)

        # Cache miss - call API
        logger.debug(f"📡 Embedding cache MISS - calling API for: '{query[:40]}...'")
        embedding = self._embedding_client.embed_query(query)
        embedding_tuple = tuple(embedding)

        # Add to cache (simple FIFO eviction if full)
        if len(self._query_cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]

        self._query_cache[cache_key] = embedding_tuple
        return np.array(embedding_tuple, dtype=np.float32)

    @staticmethod
    def _ensure_event_loop() -> None:
        """Ensure the current thread has an asyncio event loop."""
        policy = asyncio.get_event_loop_policy()
        try:
            policy.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            policy.set_event_loop(loop)
