"""
SQLite-based cache for query embeddings AND generated SQL with normalization + fuzzy matching.

This cache stores BOTH:
1. Query embeddings (saves ~250-500ms Gemini embedding API call)
2. Generated SQL (saves ~1-2 seconds LLM SQL generation call)

Two-tier matching strategy:
1. Exact match after normalization (fast, ~1ms)
2. Fuzzy string matching fallback (slower, ~10ms for 100 cached queries)

Performance Impact:
- Cache HIT (exact): ~1ms (skips BOTH embedding + LLM calls)
- Cache HIT (fuzzy): ~10ms (skips BOTH embedding + LLM calls)
- Cache MISS: ~2.5 seconds (embedding + SQL generation)
- Expected savings: 2-3 seconds per cache hit
- Expected hit rate: 55-65% for typical usage patterns

Example:
    cache = QueryEmbeddingCache(enable_fuzzy_fallback=True)

    # First query
    result = cache.get("Show me all load balancers")
    # → Cache MISS (None)

    # Generate SQL and cache it
    embedding = embed_fn(query)
    sql = generate_sql_fn(query)
    cache.set(query, embedding, sql)

    # Similar query (exact match after normalization)
    result = cache.get("List all load balancers")
    # → Exact cache HIT (1ms) - returns (embedding, sql)

    # Slightly different query (fuzzy match)
    result = cache.get("Show all load balancers")
    # → Fuzzy cache HIT (10ms) - returns (embedding, sql)
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

        logger.debug(
            f"Initialized query cache at {db_path} (fuzzy: {enable_fuzzy_fallback})"
        )

    def _create_tables(self):
        """Create cache tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS query_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_query TEXT NOT NULL,
                normalized_query TEXT NOT NULL,
                embedding BLOB NOT NULL,
                generated_sql TEXT,
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

    def _fuzzy_match(self, query: str) -> Optional[Tuple[str, List[float], Optional[str], float]]:
        """
        Find similar cached query using fuzzy string matching.

        Args:
            query: Normalized query to match

        Returns:
            Tuple of (cached_query, embedding, generated_sql, similarity) or None
        """
        if not self.enable_fuzzy_fallback:
            return None

        # Get all cached normalized queries with SQL
        cached_queries = self.conn.execute(
            "SELECT normalized_query, embedding, generated_sql FROM query_embeddings"
        ).fetchall()

        if not cached_queries:
            return None

        best_match = None
        best_similarity = 0.0

        for cached_query, embedding_blob, generated_sql in cached_queries:
            # Calculate similarity ratio
            similarity = SequenceMatcher(None, query, cached_query).ratio()

            if similarity > best_similarity and similarity >= self.fuzzy_threshold:
                best_similarity = similarity
                best_match = (cached_query, pickle.loads(embedding_blob), generated_sql, similarity)

        if best_match:
            cached_query, embedding, generated_sql, similarity = best_match
            logger.info(
                f"✅ Fuzzy cache HIT (similarity: {similarity:.2f})\n"
                f"   Query:  '{query}'\n"
                f"   Cached: '{cached_query}'\n"
                f"   SQL cached: {generated_sql is not None}"
            )
            return best_match

        return None

    def get(self, query: str) -> Optional[Tuple[List[float], Optional[str]]]:
        """
        Get cached embedding AND generated SQL for a query.

        Uses two-tier matching:
        1. Exact match after normalization (fast)
        2. Fuzzy string matching fallback (slower but catches more variations)

        Args:
            query: Query text to look up

        Returns:
            Tuple of (embedding, generated_sql) or None if not found
            - embedding: list of floats
            - generated_sql: SQL string or None if not cached
        """
        normalized = self.normalize_query(query)

        # Try exact match first (fast path)
        result = self.conn.execute(
            """
            SELECT embedding, generated_sql
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
            generated_sql = result[1]
            logger.debug(
                f"Cache HIT (exact): '{query[:60]}...' - SQL: {generated_sql is not None}"
            )
            return (embedding, generated_sql)

        # Try fuzzy matching fallback
        fuzzy_result = self._fuzzy_match(normalized)
        if fuzzy_result:
            cached_query, embedding, generated_sql, similarity = fuzzy_result

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

            return (embedding, generated_sql)

        logger.debug(f"❌ Cache MISS for query: '{query}' (normalized: '{normalized}')")
        return None

    def set(self, query: str, embedding: List[float], generated_sql: Optional[str] = None) -> None:
        """
        Store embedding and generated SQL in cache.

        Args:
            query: Original query text
            embedding: Query embedding (list of floats)
            generated_sql: Generated SQL query (optional, can be added later)
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
                SET original_query = ?, embedding = ?, generated_sql = ?, last_used_at = ?
                WHERE normalized_query = ?
                """,
                (query, pickle.dumps(embedding), generated_sql, datetime.now(), normalized)
            )
            logger.debug(f"Updated cache for normalized query: '{normalized}' (SQL: {generated_sql is not None})")
        else:
            # Insert new entry
            self.conn.execute(
                """
                INSERT INTO query_embeddings
                (original_query, normalized_query, embedding, generated_sql, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (query, normalized, pickle.dumps(embedding), generated_sql, datetime.now(), datetime.now())
            )
            logger.info(f"Cached new query: '{query}' (normalized: '{normalized}', SQL: {generated_sql is not None})")

        self.conn.commit()

    def get_or_create(self, query: str, embed_fn: Callable[[str], List[float]]) -> Tuple[List[float], Optional[str]]:
        """
        Get cached embedding/SQL or create new embedding if not found.

        Note: This only creates embeddings on cache miss, not SQL.
        For SQL caching, use get() to check cache, then call set() with SQL after generation.

        Args:
            query: Query text
            embed_fn: Function to call if cache miss (e.g., gemini.embed_query)

        Returns:
            Tuple of (embedding, generated_sql)
            - embedding: always present (from cache or newly generated)
            - generated_sql: may be None if not cached yet

        Example:
            embedding, cached_sql = cache.get_or_create(
                "Show me all servers",
                lambda q: embedding_service.embed_query(q)
            )

            if cached_sql:
                # Use cached SQL (fast path)
                return cached_sql
            else:
                # Generate SQL and cache it
                sql = generate_sql(query, embedding)
                cache.set(query, embedding, sql)
                return sql
        """
        # Try cache first
        cached = self.get(query)
        if cached is not None:
            embedding, generated_sql = cached
            return (embedding, generated_sql)

        # Cache miss - generate new embedding (but not SQL yet)
        logger.info(f"Generating new embedding for: '{query}'")
        embedding = embed_fn(query)

        # Store embedding in cache (SQL can be added later)
        self.set(query, embedding, generated_sql=None)

        return (embedding, None)

    def update_sql(self, query: str, generated_sql: str) -> bool:
        """
        Update the generated SQL for an existing cached query.

        Useful for caching SQL after embedding has already been cached.

        Args:
            query: Original query text
            generated_sql: Generated SQL to cache

        Returns:
            True if updated, False if query not found in cache

        Example:
            # First, cache comes with just embedding
            embedding, cached_sql = cache.get_or_create(query, embed_fn)

            # Later, after generating SQL
            sql = generate_sql(query, embedding)
            cache.update_sql(query, sql)
        """
        normalized = self.normalize_query(query)

        # Check if entry exists
        existing = self.conn.execute(
            "SELECT id FROM query_embeddings WHERE normalized_query = ?",
            (normalized,)
        ).fetchone()

        if not existing:
            logger.warning(f"Cannot update SQL: query '{query}' not found in cache")
            return False

        # Update SQL
        self.conn.execute(
            """
            UPDATE query_embeddings
            SET generated_sql = ?, last_used_at = ?
            WHERE normalized_query = ?
            """,
            (generated_sql, datetime.now(), normalized)
        )
        self.conn.commit()

        logger.info(f"Updated SQL cache for query: '{query}' (normalized: '{normalized}')")
        return True

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

    def invalidate(self, query: str, keep_embedding: bool = True) -> bool:
        """
        Invalidate cached SQL for a query.

        Useful when user provides negative feedback (thumbs down) on a result.
        Forces fresh SQL generation on next request.

        Args:
            query: Query text to invalidate
            keep_embedding: If True (default), only invalidate SQL and keep embedding.
                          This is faster for retries (~2s vs ~2.5s).
                          If False, delete entire cache entry (embedding + SQL).

        Returns:
            True if entry was invalidated, False if not found in cache

        Example:
            # User clicks thumbs down (default: keep embedding for faster retry)
            cache.invalidate("Show unhealthy servers")
            # Next retry: ~2 seconds (reuses embedding, regenerates SQL only)

            # Nuclear option: delete everything
            cache.invalidate("Show unhealthy servers", keep_embedding=False)
            # Next retry: ~2.5 seconds (regenerates embedding + SQL)
        """
        normalized = self.normalize_query(query)

        if keep_embedding:
            # More efficient: Only invalidate SQL, keep embedding
            # Saves ~500ms on retry (embedding API call avoided)
            cursor = self.conn.execute(
                """
                UPDATE query_embeddings
                SET generated_sql = NULL, last_used_at = ?
                WHERE normalized_query = ?
                """,
                (datetime.now(), normalized)
            )
            action = "Invalidated SQL (kept embedding)"
        else:
            # Nuclear option: Delete entire entry (embedding + SQL)
            # Use this if table selection was also wrong
            cursor = self.conn.execute(
                "DELETE FROM query_embeddings WHERE normalized_query = ?",
                (normalized,)
            )
            action = "Deleted entire cache entry (embedding + SQL)"

        affected = cursor.rowcount
        self.conn.commit()

        if affected > 0:
            logger.info(
                f"✅ {action} for query: '{query}' (normalized: '{normalized}')\n"
                f"   Affected {affected} entries\n"
                f"   Retry performance: {'~2s (fast)' if keep_embedding else '~2.5s (full regeneration)'}"
            )
            return True
        else:
            logger.debug(f"No cache entry found to invalidate: '{query}'")
            return False

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
