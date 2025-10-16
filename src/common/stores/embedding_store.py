"""
Embedding storage backends for semantic table finding.
Supports both local file cache and PostgreSQL pgvector.
"""
import os
import json
import logging
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod
import numpy as np

logger = logging.getLogger(__name__)

# Try importing psycopg2 for PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import execute_values
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("psycopg2 not available - PostgreSQL embedding store disabled")


class EmbeddingStore(ABC):
    """Abstract base class for embedding storage backends."""

    @abstractmethod
    def store(self, table_name: str, description: str, embedding: np.ndarray, namespace: str = "default"):
        """Store a table embedding.

        Args:
            table_name: Name of the table
            description: Table description
            embedding: Embedding vector (numpy array)
            namespace: Schema namespace (e.g., 'app_a', 'app_b')
        """
        pass

    @abstractmethod
    def search_similar(
        self,
        query_embedding: np.ndarray,
        namespace: str = "default",
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[str, float]]:
        """Search for similar tables.

        Args:
            query_embedding: Query embedding vector
            namespace: Schema namespace to search within
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of (table_name, similarity_score) tuples
        """
        pass

    @abstractmethod
    def get_embedding(self, table_name: str, namespace: str = "default") -> Optional[np.ndarray]:
        """Retrieve embedding for a specific table.

        Args:
            table_name: Name of the table
            namespace: Schema namespace

        Returns:
            Embedding vector or None if not found
        """
        pass

    @abstractmethod
    def clear_namespace(self, namespace: str):
        """Clear all embeddings for a specific namespace.

        Args:
            namespace: Schema namespace to clear
        """
        pass


class LocalFileEmbeddingStore(EmbeddingStore):
    """File-based embedding storage (legacy, for development)."""

    def __init__(self, cache_dir: str = ".embeddings_cache"):
        """Initialize local file embedding store.

        Args:
            cache_dir: Base directory for cache files
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_namespace_dir(self, namespace: str) -> str:
        """Get directory for a specific namespace."""
        path = os.path.join(self.cache_dir, namespace)
        os.makedirs(path, exist_ok=True)
        return path

    def _get_cache_path(self, namespace: str) -> str:
        """Get cache file path for namespace."""
        return os.path.join(self._get_namespace_dir(namespace), "embeddings.json")

    def _load_cache(self, namespace: str) -> dict:
        """Load embedding cache from file."""
        cache_path = self._get_cache_path(namespace)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    # Convert lists back to numpy arrays
                    for table_name in data:
                        data[table_name]['embedding'] = np.array(data[table_name]['embedding'])
                    return data
            except Exception as e:
                logger.warning(f"Failed to load cache from {cache_path}: {e}")
        return {}

    def _save_cache(self, cache: dict, namespace: str):
        """Save embedding cache to file."""
        cache_path = self._get_cache_path(namespace)
        # Convert numpy arrays to lists for JSON serialization
        serializable_cache = {}
        for table_name, data in cache.items():
            serializable_cache[table_name] = {
                'description': data['description'],
                'embedding': data['embedding'].tolist()
            }
        with open(cache_path, 'w') as f:
            json.dump(serializable_cache, f)

    def store(self, table_name: str, description: str, embedding: np.ndarray, namespace: str = "default"):
        """Store a table embedding."""
        cache = self._load_cache(namespace)
        cache[table_name] = {
            'description': description,
            'embedding': embedding
        }
        self._save_cache(cache, namespace)
        logger.debug(f"Stored embedding for {table_name} in namespace {namespace}")

    def search_similar(
        self,
        query_embedding: np.ndarray,
        namespace: str = "default",
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[str, float]]:
        """Search for similar tables using cosine similarity."""
        cache = self._load_cache(namespace)
        if not cache:
            return []

        # Calculate cosine similarity for all tables
        similarities = []
        for table_name, data in cache.items():
            table_embedding = data['embedding']
            # Cosine similarity
            similarity = np.dot(query_embedding, table_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(table_embedding)
            )
            if similarity >= min_similarity:
                similarities.append((table_name, float(similarity)))

        # Sort by similarity (descending) and limit
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    def get_embedding(self, table_name: str, namespace: str = "default") -> Optional[np.ndarray]:
        """Retrieve embedding for a specific table."""
        cache = self._load_cache(namespace)
        if table_name in cache:
            return cache[table_name]['embedding']
        return None

    def clear_namespace(self, namespace: str):
        """Clear all embeddings for a specific namespace."""
        namespace_dir = self._get_namespace_dir(namespace)
        cache_path = self._get_cache_path(namespace)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            logger.info(f"Cleared namespace {namespace}")


class PgVectorEmbeddingStore(EmbeddingStore):
    """PostgreSQL + pgvector embedding storage."""

    def __init__(self, database_url: str):
        """Initialize pgvector embedding store.

        Args:
            database_url: PostgreSQL connection URL (postgresql://user:pass@host:port/dbname)
        """
        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 is not installed. Install with: pip install psycopg2-binary")

        self.database_url = database_url
        self._ensure_extension()

    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.database_url)

    def _ensure_extension(self):
        """Ensure pgvector extension is enabled."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("pgvector extension enabled")
        except Exception as e:
            logger.error(f"Failed to enable pgvector extension: {e}")
            raise

    def store(self, table_name: str, description: str, embedding: np.ndarray, namespace: str = "default"):
        """Store a table embedding in PostgreSQL."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Upsert: insert or update if exists
            cursor.execute("""
                INSERT INTO embeddings (schema_id, table_name, description, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (schema_id, table_name)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    embedding = EXCLUDED.embedding,
                    updated_at = NOW()
            """, (namespace, table_name, description, embedding.tolist()))

            conn.commit()
            logger.debug(f"Stored embedding for {table_name} in namespace {namespace}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to store embedding for {table_name}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def search_similar(
        self,
        query_embedding: np.ndarray,
        namespace: str = "default",
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[str, float]]:
        """Search for similar tables using pgvector cosine distance.

        Note: pgvector uses cosine distance (<=>), so we convert to similarity (1 - distance/2)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # pgvector cosine distance operator: <=>
            # Convert distance to similarity: similarity = 1 - (distance / 2)
            # This gives us a 0-1 similarity score
            cursor.execute("""
                SELECT
                    table_name,
                    1 - (embedding <=> %s::vector) / 2 AS similarity
                FROM embeddings
                WHERE schema_id = %s
                    AND 1 - (embedding <=> %s::vector) / 2 >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (
                query_embedding.tolist(),
                namespace,
                query_embedding.tolist(),
                min_similarity,
                query_embedding.tolist(),
                limit
            ))

            results = [(row[0], float(row[1])) for row in cursor.fetchall()]
            logger.debug(f"Found {len(results)} similar tables in namespace {namespace}")
            return results

        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def get_embedding(self, table_name: str, namespace: str = "default") -> Optional[np.ndarray]:
        """Retrieve embedding for a specific table."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT embedding
                FROM embeddings
                WHERE schema_id = %s AND table_name = %s
            """, (namespace, table_name))

            row = cursor.fetchone()
            if row:
                # pgvector returns the embedding as a list
                return np.array(row[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get embedding for {table_name}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def clear_namespace(self, namespace: str):
        """Clear all embeddings for a specific namespace."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM embeddings
                WHERE schema_id = %s
            """, (namespace,))

            conn.commit()
            logger.info(f"Cleared {cursor.rowcount} embeddings from namespace {namespace}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to clear namespace {namespace}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()


def create_embedding_store(database_url: Optional[str] = None, cache_dir: str = ".embeddings_cache") -> EmbeddingStore:
    """Factory function to create appropriate embedding store.

    Args:
        database_url: Database URL. If starts with 'postgresql://', uses PgVectorEmbeddingStore.
                     Otherwise uses LocalFileEmbeddingStore.
        cache_dir: Cache directory for local file store (ignored for pgvector)

    Returns:
        EmbeddingStore instance
    """
    if database_url and database_url.startswith('postgresql'):
        logger.info(f"Using PgVectorEmbeddingStore with {database_url}")
        return PgVectorEmbeddingStore(database_url)
    else:
        logger.info(f"Using LocalFileEmbeddingStore with cache_dir={cache_dir}")
        return LocalFileEmbeddingStore(cache_dir)
