"""
Simplified SQLite-based cache for generated SQL with normalization + fuzzy matching.

This cache stores ONLY generated SQL queries, not embeddings.

Matching strategy:
1. Exact match after normalization (fast, ~1ms)
2. Fuzzy string matching fallback (slower, ~10ms for 100 cached queries)

Performance Impact:
- Cache HIT (exact): ~1ms (skips SQL generation ~2s)
- Cache HIT (fuzzy): ~10ms (skips SQL generation ~2s)
- Cache MISS: ~2.5 seconds (embedding + SQL generation)
- Expected savings: ~2 seconds per cache hit
- Expected hit rate: 60-80% for typical usage patterns

Example:
    cache = SQLCache(enable_fuzzy_fallback=True)

    # First query
    result = cache.get("Show me all load balancers")
    # → Cache MISS (None)

    # Generate SQL and cache it
    sql = generate_sql_fn(query)
    cache.set(query, sql)

    # Similar query (exact match after normalization)
    result = cache.get("List all load balancers")
    # → Exact cache HIT (1ms) - returns sql

    # Slightly different query (fuzzy match)
    result = cache.get("Show all load balancers")
    # → Fuzzy cache HIT (10ms) - returns sql
"""
import sqlite3
import logging
import re
from pathlib import Path
from typing import Optional
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class SQLCache:
    """SQLite-based cache for generated SQL with normalization + fuzzy matching."""

    def __init__(
        self,
        db_path: str = "data/sql_cache.db",
        enable_fuzzy_fallback: bool = True,
        fuzzy_threshold: float = 0.85
    ):
        """
        Initialize the SQL cache.

        Args:
            db_path: Path to SQLite database file (created if doesn't exist, default: data/sql_cache.db)
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
            f"Initialized SQL cache at {db_path} (fuzzy: {enable_fuzzy_fallback})"
        )

    def _create_tables(self):
        """Create cache tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sql_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_query TEXT NOT NULL,
                normalized_query TEXT NOT NULL UNIQUE,
                generated_sql TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hit_count INTEGER DEFAULT 1
            )
        """)

        # Index on normalized query for fast lookups
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_normalized_query
            ON sql_cache(normalized_query)
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

    def _fuzzy_match(self, query: str) -> Optional[tuple[str, float]]:
        """
        Find similar cached query using fuzzy string matching.

        Args:
            query: Normalized query to match

        Returns:
            Tuple of (cached_sql, similarity) or None
        """
        if not self.enable_fuzzy_fallback:
            return None

        # Get all cached normalized queries with SQL
        cached_queries = self.conn.execute(
            "SELECT normalized_query, generated_sql FROM sql_cache"
        ).fetchall()

        if not cached_queries:
            return None

        best_match = None
        best_similarity = 0.0

        for cached_query, generated_sql in cached_queries:
            # Calculate similarity ratio
            similarity = SequenceMatcher(None, query, cached_query).ratio()

            if similarity > best_similarity and similarity >= self.fuzzy_threshold:
                best_similarity = similarity
                best_match = (generated_sql, similarity)

        if best_match:
            cached_sql, similarity = best_match
            logger.info(
                f"Fuzzy cache HIT (similarity: {similarity:.2f})\n"
                f"   Query:  '{query}'\n"
                f"   Matched cached query with SQL"
            )
            # Update hit count for the matched query
            self.conn.execute(
                """
                UPDATE sql_cache
                SET last_used_at = ?, hit_count = hit_count + 1
                WHERE generated_sql = ?
                """,
                (datetime.now(), cached_sql)
            )
            self.conn.commit()
            return best_match

        return None

    def get(self, query: str) -> Optional[str]:
        """
        Get cached SQL for a query.

        Uses two-tier matching:
        1. Exact match after normalization (fast)
        2. Fuzzy string matching fallback (slower but catches more variations)

        Args:
            query: Query text to look up

        Returns:
            SQL string or None if not found
        """
        normalized = self.normalize_query(query)

        # Try exact match first (fast path)
        result = self.conn.execute(
            """
            SELECT generated_sql
            FROM sql_cache
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
                UPDATE sql_cache
                SET last_used_at = ?, hit_count = hit_count + 1
                WHERE normalized_query = ?
                """,
                (datetime.now(), normalized)
            )
            self.conn.commit()

            generated_sql = result[0]
            logger.debug(f"Cache HIT (exact): '{query[:60]}...'")
            return generated_sql

        # Try fuzzy matching fallback
        fuzzy_result = self._fuzzy_match(normalized)
        if fuzzy_result:
            cached_sql, similarity = fuzzy_result
            return cached_sql

        logger.debug(f"Cache MISS for query: '{query}' (normalized: '{normalized}')")
        return None

    def set(self, query: str, generated_sql: str) -> None:
        """
        Store generated SQL in cache.

        Args:
            query: Original query text
            generated_sql: Generated SQL query
        """
        normalized = self.normalize_query(query)

        # Check if normalized query already exists
        existing = self.conn.execute(
            "SELECT id FROM sql_cache WHERE normalized_query = ?",
            (normalized,)
        ).fetchone()

        if existing:
            # Update existing entry
            self.conn.execute(
                """
                UPDATE sql_cache
                SET original_query = ?, generated_sql = ?, last_used_at = ?
                WHERE normalized_query = ?
                """,
                (query, generated_sql, datetime.now(), normalized)
            )
            logger.debug(f"Updated cache for normalized query: '{normalized}'")
        else:
            # Insert new entry
            self.conn.execute(
                """
                INSERT INTO sql_cache
                (original_query, normalized_query, generated_sql, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (query, normalized, generated_sql, datetime.now(), datetime.now())
            )
            logger.info(f"Cached new query: '{query}' (normalized: '{normalized}')")

        self.conn.commit()

    def invalidate(self, query: str) -> bool:
        """
        Invalidate cached SQL for a query.

        Useful when user provides negative feedback (thumbs down) on a result.
        Forces fresh SQL generation on next request.

        Args:
            query: Query text to invalidate

        Returns:
            True if entry was deleted, False if not found in cache

        Example:
            # User clicks thumbs down
            cache.invalidate("Show unhealthy servers")
            # Next retry: ~2.5 seconds (regenerates everything)
        """
        normalized = self.normalize_query(query)

        cursor = self.conn.execute(
            "DELETE FROM sql_cache WHERE normalized_query = ?",
            (normalized,)
        )

        affected = cursor.rowcount
        self.conn.commit()

        if affected > 0:
            logger.info(
                f"Deleted cache entry for query: '{query}' (normalized: '{normalized}')\n"
                f"   Affected {affected} entries\n"
                f"   Next retry will regenerate SQL (~2.5s)"
            )
            return True
        else:
            logger.debug(f"No cache entry found to invalidate: '{query}'")
            return False

    def clear(self) -> int:
        """
        Clear all cached SQL.

        Returns:
            Number of entries deleted
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM sql_cache")
        count = cursor.fetchone()[0]

        self.conn.execute("DELETE FROM sql_cache")
        self.conn.commit()

        logger.info(f"Cleared {count} cached SQL entries")
        return count

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {}

        cursor = self.conn.execute("SELECT COUNT(*) FROM sql_cache")
        stats['total_entries'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT SUM(hit_count) FROM sql_cache")
        stats['total_hits'] = cursor.fetchone()[0] or 0

        cursor = self.conn.execute(
            """
            SELECT original_query, normalized_query, hit_count, last_used_at
            FROM sql_cache
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
            DELETE FROM sql_cache
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
            logger.debug("Closed SQL cache")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
