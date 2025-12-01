"""Shared embedding service abstractions."""
from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Optional

import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..config import config

logger = logging.getLogger(__name__)

# Module-level LRU cache for query embeddings (shared across instances)
# Caches up to 128 query embeddings to avoid repeated API calls
@lru_cache(maxsize=128)
def _cached_embed_query(query: str, model_name: str, api_key: str) -> tuple:
    """
    Cached embedding generation for queries.

    Returns tuple instead of np.ndarray because lru_cache requires hashable return values.
    The tuple is converted back to np.ndarray by the caller.
    """
    client = GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)
    embedding = client.embed_query(query)
    return tuple(embedding)


class EmbeddingService:
    """Thin wrapper around Gemini embeddings for consistent usage with caching."""

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

        Uses an LRU cache to avoid repeated API calls for the same query.
        Cache hit saves ~100-150ms per query.
        """
        # Normalize query for better cache hits
        normalized_query = query.lower().strip()

        # Check if we got a cache hit (for logging)
        cache_info_before = _cached_embed_query.cache_info()

        # Get cached or compute new embedding
        embedding_tuple = _cached_embed_query(
            normalized_query,
            self.model_name,
            self._api_key
        )

        cache_info_after = _cached_embed_query.cache_info()
        if cache_info_after.hits > cache_info_before.hits:
            logger.debug(f"⚡ Embedding cache HIT for query: '{query[:40]}...'")
        else:
            logger.debug(f"📡 Embedding cache MISS - called API for: '{query[:40]}...'")

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
