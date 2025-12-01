"""
Embedding storage backends for semantic table finding.
Supports SQLite (default) and PostgreSQL pgvector.
"""
import os
import json
import sqlite3
import pickle
import logging
from pathlib import Path
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


class SQLiteEmbeddingStore(EmbeddingStore):
    """SQLite-based embedding storage (default, recommended)."""

    def __init__(self, db_path: str = "data/embeddings_cache.db"):
        """Initialize SQLite embedding store.

        Args:
            db_path: Path to SQLite database file
        """
        # Create directory if needed
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        logger.debug(f"Initialized SQLite embedding store at {db_path}")

    def _create_tables(self):
        """Create embedding tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT NOT NULL,
                table_name TEXT NOT NULL,
                description TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(namespace, table_name)
            )
        """)

        # Index for fast lookups by namespace
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_namespace
            ON schema_embeddings(namespace)
        """)

        # Index for fast lookups by namespace + table_name
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_namespace_table
            ON schema_embeddings(namespace, table_name)
        """)

        self.conn.commit()

    def store(self, table_name: str, description: str, embedding: np.ndarray, namespace: str = "default"):
        """Store a table embedding."""
        # Serialize embedding as pickle blob
        embedding_blob = pickle.dumps(embedding)

        # Insert or replace
        self.conn.execute(
            """
            INSERT OR REPLACE INTO schema_embeddings
            (namespace, table_name, description, embedding, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (namespace, table_name, description, embedding_blob)
        )
        self.conn.commit()
        logger.debug(f"Stored embedding for {table_name} in namespace {namespace}")

    def search_similar(
        self,
        query_embedding: np.ndarray,
        namespace: str = "default",
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[str, float]]:
        """Search for similar tables using cosine similarity."""
        # Fetch all embeddings for this namespace
        cursor = self.conn.execute(
            "SELECT table_name, embedding FROM schema_embeddings WHERE namespace = ?",
            (namespace,)
        )

        results = cursor.fetchall()
        if not results:
            return []

        # Calculate cosine similarity for all tables
        similarities = []
        for table_name, embedding_blob in results:
            table_embedding = pickle.loads(embedding_blob)

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
        cursor = self.conn.execute(
            "SELECT embedding FROM schema_embeddings WHERE namespace = ? AND table_name = ?",
            (namespace, table_name)
        )

        result = cursor.fetchone()
        if result:
            return pickle.loads(result[0])
        return None

    def clear_namespace(self, namespace: str):
        """Clear all embeddings for a specific namespace."""
        cursor = self.conn.execute(
            "DELETE FROM schema_embeddings WHERE namespace = ?",
            (namespace,)
        )
        deleted = cursor.rowcount
        self.conn.commit()
        logger.info(f"Cleared namespace {namespace} ({deleted} embeddings deleted)")

    def get_stats(self, namespace: str = None) -> dict:
        """Get statistics about stored embeddings.

        Args:
            namespace: Optional namespace to filter stats

        Returns:
            Dictionary with statistics
        """
        stats = {}

        if namespace:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM schema_embeddings WHERE namespace = ?",
                (namespace,)
            )
            stats['total_embeddings'] = cursor.fetchone()[0]
            stats['namespace'] = namespace
        else:
            cursor = self.conn.execute("SELECT COUNT(*) FROM schema_embeddings")
            stats['total_embeddings'] = cursor.fetchone()[0]

            cursor = self.conn.execute(
                "SELECT namespace, COUNT(*) FROM schema_embeddings GROUP BY namespace"
            )
            stats['by_namespace'] = {row[0]: row[1] for row in cursor.fetchall()}

        return stats

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Closed SQLite embedding store")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


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


def create_embedding_store(
    database_url: Optional[str] = None,
    db_path: str = "data/embeddings_cache.db"
) -> EmbeddingStore:
    """Factory function to create appropriate embedding store.

    Priority order:
    1. PostgreSQL pgvector (if EMBEDDING_DATABASE_URL is postgresql://)
    2. SQLite (default, recommended)

    Args:
        database_url: Database URL. If starts with 'postgresql://', uses PgVectorEmbeddingStore.
        db_path: Path to SQLite database (default: data/embeddings_cache.db)

    Returns:
        EmbeddingStore instance
    """
    # Option 1: PostgreSQL pgvector (production with vector similarity indexing)
    if database_url and database_url.startswith('postgresql'):
        logger.debug(f"Using PgVectorEmbeddingStore with {database_url}")
        return PgVectorEmbeddingStore(database_url)

    # Option 2: Default to SQLite (recommended for most cases)
    logger.debug(f"Using SQLiteEmbeddingStore (default) with db_path={db_path}")
    return SQLiteEmbeddingStore(db_path)
