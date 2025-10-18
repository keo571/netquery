"""Shared embedding service abstractions."""
from __future__ import annotations

from typing import Optional

import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..config import config


class EmbeddingService:
    """Thin wrapper around Gemini embeddings for consistent usage."""

    def __init__(self, model_name: str = "gemini-embedding-001", api_key: Optional[str] = None) -> None:
        self.model_name = model_name
        self._api_key = api_key or config.llm.effective_api_key
        self._embedding_client = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=self._api_key,
        )

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single document-sized text snippet."""
        embedding = self._embedding_client.embed_documents([text])[0]
        return np.array(embedding, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a user query for similarity search."""
        embedding = self._embedding_client.embed_query(query)
        return np.array(embedding, dtype=np.float32)
