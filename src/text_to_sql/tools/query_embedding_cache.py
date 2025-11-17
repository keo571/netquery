"""
SQLite-based cache for query embeddings with normalization + fuzzy matching fallback.

This cache stores query embeddings to avoid repeated Gemini API calls for similar queries.

Two-tier matching strategy:
1. Exact match after normalization (fast, ~1ms)
2. Fuzzy string matching fallback (slower, ~10ms for 100 cached queries)

Performance Impact:
- Cache HIT (exact): ~1ms
- Cache HIT (fuzzy): ~10ms (vs 250-500ms Gemini API call)
- Cache MISS: ~511ms (10ms check + 500ms API call)
- Expected hit rate: 55-65% for typical usage patterns

Example:
    cache = QueryEmbeddingCache(enable_fuzzy_fallback=True)

    # First query
    embedding = cache.get_or_create("Show me all load balancers", embed_fn)
    # → Cache MISS, calls embed_fn() (500ms)

    # Similar query (exact match after normalization)
    embedding = cache.get_or_create("List all load balancers", embed_fn)
    # → Exact cache HIT (1ms)

    # Slightly different query (fuzzy match)
    embedding = cache.get_or_create("Show all load balancers", embed_fn)
    # → Fuzzy cache HIT (10ms)
"""
import sqlite3
import pickle
import logging
import re
from pathlib import Path
from typing import Optional, List, Callable, Tuple
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class QueryEmbeddingCache:
    """SQLite-based cache for query embeddings with normalization + fuzzy matching."""

    def __init__(
        self,
        db_path: str = ".embeddings_cache/query_cache.db",
        enable_fuzzy_fallback: bool = True,
        fuzzy_threshold: float = 0.85
    ):
        """
        Initialize the embedding cache.

        Args:
            db_path: Path to SQLite database file (created if doesn't exist)
            enable_fuzzy_fallback: Enable fuzzy string matching as fallback (default: True)
            fuzzy_threshold: Minimum similarity ratio for fuzzy matching (0.0-1.0, default: 0.85)
        """
        # Create cache directory if needed
        cache_dir = Path(db_path).parent
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.enable_fuzzy_fallback = enable_fuzzy_fallback
        self.fuzzy_threshold = fuzzy_threshold
        self._create_tables()

        logger.info(
            f"Initialized query embedding cache at {db_path} "
            f"(fuzzy fallback: {enable_fuzzy_fallback})"
        )

    def _create_tables(self):
        """Create cache tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS query_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_query TEXT NOT NULL,
                normalized_query TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hit_count INTEGER DEFAULT 1
            )
        """)

        # Index on normalized query for fast lookups
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_normalized_query
            ON query_embeddings(normalized_query)
        """)

        self.conn.commit()

    def normalize_query(self, query: str) -> str:
        """
        Normalize query to match similar variations.

        Normalization steps:
        1. Convert to lowercase
        2. Remove common action verbs (show, list, display, get, find)
        3. Remove punctuation
        4. Normalize whitespace

        Examples:
            "Show me all load balancers" → "all load balancers"
            "List all load balancers" → "all load balancers"
            "Display load balancers" → "load balancers"
            "Get unhealthy servers" → "unhealthy servers"

        Args:
            query: Original query text

        Returns:
            Normalized query string
        """
        # Convert to lowercase
        normalized = query.lower().strip()

        # Remove common action verbs (order matters - more specific first)
        action_verbs = [
            "show me all", "show me", "show all", "show",
            "list all", "list",
            "display all", "display",
            "get all", "get",
            "find all", "find",
            "give me all", "give me",
            "fetch all", "fetch",
            "retrieve all", "retrieve",
        ]

        for verb in action_verbs:
            if normalized.startswith(verb + " "):
                normalized = normalized[len(verb):].strip()
                break

        # Remove punctuation except hyphens and underscores
        normalized = re.sub(r'[^\w\s\-_]', ' ', normalized)

        # Normalize whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def _fuzzy_match(self, query: str) -> Optional[Tuple[str, List[float], float]]:
        """
        Find similar cached query using fuzzy string matching.

        Args:
            query: Normalized query to match

        Returns:
            Tuple of (cached_query, embedding, similarity) or None
        """
        if not self.enable_fuzzy_fallback:
            return None

        # Get all cached normalized queries
        cached_queries = self.conn.execute(
            "SELECT normalized_query, embedding FROM query_embeddings"
        ).fetchall()

        if not cached_queries:
            return None

        best_match = None
        best_similarity = 0.0

        for cached_query, embedding_blob in cached_queries:
            # Calculate similarity ratio
            similarity = SequenceMatcher(None, query, cached_query).ratio()

            if similarity > best_similarity and similarity >= self.fuzzy_threshold:
                best_similarity = similarity
                best_match = (cached_query, pickle.loads(embedding_blob), similarity)

        if best_match:
            cached_query, embedding, similarity = best_match
            logger.info(
                f"✅ Fuzzy cache HIT (similarity: {similarity:.2f})\n"
                f"   Query:  '{query}'\n"
                f"   Cached: '{cached_query}'"
            )
            return best_match

        return None

    def get(self, query: str) -> Optional[List[float]]:
        """
        Get cached embedding for a query.

        Uses two-tier matching:
        1. Exact match after normalization (fast)
        2. Fuzzy string matching fallback (slower but catches more variations)

        Args:
            query: Query text to look up

        Returns:
            Cached embedding (list of floats) or None if not found
        """
        normalized = self.normalize_query(query)

        # Try exact match first (fast path)
        result = self.conn.execute(
            """
            SELECT embedding
            FROM query_embeddings
            WHERE normalized_query = ?
            ORDER BY last_used_at DESC
            LIMIT 1
            """,
            (normalized,)
        ).fetchone()

        if result:
            # Update usage statistics
            self.conn.execute(
                """
                UPDATE query_embeddings
                SET last_used_at = ?, hit_count = hit_count + 1
                WHERE normalized_query = ?
                """,
                (datetime.now(), normalized)
            )
            self.conn.commit()

            embedding = pickle.loads(result[0])
            logger.info(
                f"✅ Exact cache HIT: '{query}' (normalized: '{normalized}')"
            )
            return embedding

        # Try fuzzy matching fallback
        fuzzy_result = self._fuzzy_match(normalized)
        if fuzzy_result:
            cached_query, embedding, similarity = fuzzy_result

            # Update usage stats for the matched query
            self.conn.execute(
                """
                UPDATE query_embeddings
                SET last_used_at = ?, hit_count = hit_count + 1
                WHERE normalized_query = ?
                """,
                (datetime.now(), cached_query)
            )
            self.conn.commit()

            return embedding

        logger.debug(f"❌ Cache MISS for query: '{query}' (normalized: '{normalized}')")
        return None

    def set(self, query: str, embedding: List[float]) -> None:
        """
        Store embedding in cache.

        Args:
            query: Original query text
            embedding: Query embedding (list of floats)
        """
        normalized = self.normalize_query(query)

        # Check if normalized query already exists
        existing = self.conn.execute(
            "SELECT id FROM query_embeddings WHERE normalized_query = ?",
            (normalized,)
        ).fetchone()

        if existing:
            # Update existing entry
            self.conn.execute(
                """
                UPDATE query_embeddings
                SET original_query = ?, embedding = ?, last_used_at = ?
                WHERE normalized_query = ?
                """,
                (query, pickle.dumps(embedding), datetime.now(), normalized)
            )
            logger.debug(f"Updated cache for normalized query: '{normalized}'")
        else:
            # Insert new entry
            self.conn.execute(
                """
                INSERT INTO query_embeddings
                (original_query, normalized_query, embedding, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (query, normalized, pickle.dumps(embedding), datetime.now(), datetime.now())
            )
            logger.info(f"Cached new query: '{query}' (normalized: '{normalized}')")

        self.conn.commit()

    def get_or_create(self, query: str, embed_fn: Callable[[str], List[float]]) -> List[float]:
        """
        Get cached embedding or create new one if not found.

        This is the main method to use. It handles cache lookup and fallback
        to embedding generation automatically.

        Args:
            query: Query text
            embed_fn: Function to call if cache miss (e.g., gemini.embed_query)

        Returns:
            Query embedding (either from cache or newly generated)

        Example:
            embedding = cache.get_or_create(
                "Show me all servers",
                lambda q: embedding_service.embed_query(q)
            )
        """
        # Try cache first
        cached = self.get(query)
        if cached is not None:
            return cached

        # Cache miss - generate new embedding
        logger.info(f"Generating new embedding for: '{query}'")
        embedding = embed_fn(query)

        # Store in cache for future use
        self.set(query, embedding)

        return embedding

    def clear(self) -> int:
        """
        Clear all cached embeddings.

        Returns:
            Number of entries deleted
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM query_embeddings")
        count = cursor.fetchone()[0]

        self.conn.execute("DELETE FROM query_embeddings")
        self.conn.commit()

        logger.info(f"Cleared {count} cached embeddings")
        return count

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {}

        cursor = self.conn.execute("SELECT COUNT(*) FROM query_embeddings")
        stats['total_entries'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT SUM(hit_count) FROM query_embeddings")
        stats['total_hits'] = cursor.fetchone()[0] or 0

        cursor = self.conn.execute(
            """
            SELECT original_query, normalized_query, hit_count, last_used_at
            FROM query_embeddings
            ORDER BY hit_count DESC
            LIMIT 10
            """
        )
        stats['top_queries'] = [
            {
                'original': row[0],
                'normalized': row[1],
                'hits': row[2],
                'last_used': row[3]
            }
            for row in cursor.fetchall()
        ]

        return stats

    def prune_old_entries(self, days: int = 30) -> int:
        """
        Remove cache entries older than specified days and never reused.

        Args:
            days: Remove entries not used in this many days

        Returns:
            Number of entries deleted
        """
        cursor = self.conn.execute(
            """
            DELETE FROM query_embeddings
            WHERE hit_count = 1
            AND datetime(last_used_at) < datetime('now', '-' || ? || ' days')
            """,
            (days,)
        )

        deleted = cursor.rowcount
        self.conn.commit()

        logger.info(f"Pruned {deleted} old cache entries (older than {days} days)")
        return deleted

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Closed query embedding cache")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
