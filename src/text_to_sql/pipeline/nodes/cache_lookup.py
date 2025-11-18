"""
Cache lookup node - checks for cached SQL before expensive pipeline processing.

This node checks if we have both cached embeddings AND cached SQL for the query.
If we have cached SQL, we can skip the entire pipeline (schema analysis + SQL generation).

Performance Impact:
- Cache HIT with SQL: Skip to validator (~1-10ms vs ~2-3 seconds)
- Cache HIT with embedding only: Skip to schema analyzer (~500ms saved)
- Cache MISS: Continue to normal pipeline flow

This maximizes the value of our two-tier caching strategy:
1. SQL cache: Ultimate fast path (skip everything)
2. Embedding cache: Partial fast path (skip embedding API call in schema analysis)

Follow-up Question Handling:
- Full cache HIT: Use cached SQL directly (no rewriting needed)
- Partial/MISS: Rewrite follow-up to standalone query for accurate table selection
"""
import logging
import os
from typing import Dict, Any
from ..state import TextToSQLState, create_success_step
from ...tools.query_embedding_cache import QueryEmbeddingCache
from ...utils.query_extraction import extract_current_query
from ...utils.query_rewriter import rewrite_if_needed

logger = logging.getLogger(__name__)

# Global query cache instance (shared across all pipeline runs)
_query_cache = None


def _get_query_cache() -> QueryEmbeddingCache:
    """Get or create the global query cache instance."""
    global _query_cache
    if _query_cache is None:
        cache_dir = os.getenv("EMBEDDING_CACHE_DIR", ".embeddings_cache")
        cache_db_path = os.path.join(cache_dir, "query_cache.db")
        _query_cache = QueryEmbeddingCache(
            db_path=cache_db_path,
            enable_fuzzy_fallback=True,
            fuzzy_threshold=0.85
        )
        logger.debug(f"Initialized global query cache at {cache_db_path}")
    return _query_cache


def _handle_full_cache_hit(extracted_query: str, embedding, cached_sql: str) -> Dict[str, Any]:
    """
    Handle FULL cache hit (have both embedding AND SQL).

    This is the fastest path - we can skip the entire pipeline!
    No rewriting needed since we already have the final SQL.

    Returns:
        State updates for full cache hit
    """
    logger.info(f"🚀 FULL cache HIT - returning cached SQL (~2-3s saved)")

    return {
        "cached_sql": cached_sql,
        "cached_embedding": embedding,
        "cache_hit_type": "full",
        "generated_sql": cached_sql,
        "query_for_embedding": extracted_query,  # Not used, but set for consistency
        "reasoning_log": [create_success_step(
            "Cache Lookup",
            "Full cache HIT - retrieved SQL and embedding from cache. "
            "Skipped schema analysis and SQL generation (~2-3 seconds saved)."
        )]
    }


def _handle_partial_cache_hit(
    full_query: str,
    extracted_query: str,
    cached_embedding
) -> Dict[str, Any]:
    """
    Handle PARTIAL cache hit (have embedding but NO SQL).

    We need to do table selection, so:
    1. Check if this is a follow-up question
    2. If yes, rewrite it for accurate table selection
    3. If rewritten, discard cached embedding (it's for wrong query)
    4. If not rewritten, use cached embedding

    Returns:
        State updates for partial cache hit
    """
    # Rewrite follow-ups for accurate table selection
    query_for_embedding = rewrite_if_needed(full_query, extracted_query, cache_hit_type="partial")

    logger.info(f"⚡ PARTIAL cache HIT - reusing embedding (~500ms saved)")

    # Decision: Was the query rewritten?
    if query_for_embedding != extracted_query:
        # REWRITTEN - cached embedding is useless (it's for the original, not rewritten query)
        logger.info(f"Follow-up detected - rewriting query for table selection")
        return {
            "cache_hit_type": None,  # Treat as miss for embedding
            "query_for_embedding": query_for_embedding,
            "reasoning_log": [create_success_step(
                "Cache Lookup",
                f"Partial cache HIT but follow-up detected. Rewrote query for accurate table selection. "
                f"Will generate embedding for: '{query_for_embedding[:60]}...'"
            )]
        }
    else:
        # NOT REWRITTEN - use cached embedding
        return {
            "cached_embedding": cached_embedding,
            "cache_hit_type": "partial",
            "query_for_embedding": extracted_query,
            "reasoning_log": [create_success_step(
                "Cache Lookup",
                "Partial cache HIT - retrieved embedding from cache. "
                "Will skip embedding API call (~500ms saved) but still need to generate SQL."
            )]
        }


def _handle_cache_miss(full_query: str, extracted_query: str) -> Dict[str, Any]:
    """
    Handle cache MISS (no cached data).

    Rewrite follow-ups for accurate table selection.

    Returns:
        State updates for cache miss
    """
    # Rewrite follow-ups for accurate table selection
    query_for_embedding = rewrite_if_needed(full_query, extracted_query, cache_hit_type=None)

    if query_for_embedding != extracted_query:
        logger.info(f"Cache MISS - follow-up detected, rewriting for table selection")
        rewrite_note = f" Rewrote follow-up query for accurate table selection."
    else:
        logger.info(f"Cache MISS - generating embedding and SQL from scratch")
        rewrite_note = ""

    return {
        "cache_hit_type": None,
        "query_for_embedding": query_for_embedding,
        "reasoning_log": [create_success_step(
            "Cache Lookup",
            f"Cache MISS - will generate embedding and SQL from scratch.{rewrite_note}"
        )]
    }


def cache_lookup_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Cache lookup with smart query rewriting for maximum performance.

    Flow:
    1. Extract query from conversation context
    2. Check cache with extracted query
    3. Route to appropriate handler based on cache result:
       - FULL HIT (have SQL)    → Return immediately (fastest, ~10ms)
       - PARTIAL HIT (embedding)→ Rewrite if needed, may keep/discard embedding
       - MISS                   → Rewrite if needed, generate from scratch

    Performance:
    - Full hit:    ~10ms (skip entire pipeline)
    - Partial hit: ~2s (skip embedding API or ~2.2s if rewritten)
    - Miss:        ~2.5s (or ~2.7s if follow-up rewritten)

    Returns:
        State updates with cache results and query variants
    """
    # ================================================================
    # Step 1: Extract query from conversation context
    # ================================================================
    # Example: "CONVERSATION HISTORY...\nUSER'S NEW QUESTION: which are unhealthy?"
    #          → Extracts: "which are unhealthy?"
    full_query = state["original_query"]
    extracted_query = extract_current_query(full_query)

    # ================================================================
    # Step 2: Check cache with extracted query
    # ================================================================
    query_cache = _get_query_cache()
    cached_result = query_cache.get(extracted_query)  # Returns (embedding, sql) or None

    # ================================================================
    # Step 3: Route to appropriate handler
    # ================================================================
    # Base state (always include these)
    base_state = {
        "query_cache": query_cache,
        "extracted_query": extracted_query
    }

    if cached_result:
        embedding, cached_sql = cached_result

        if cached_sql:
            # Path 1: FULL HIT - Fastest path!
            handler_result = _handle_full_cache_hit(extracted_query, embedding, cached_sql)
        else:
            # Path 2: PARTIAL HIT - Have embedding, may rewrite
            handler_result = _handle_partial_cache_hit(full_query, extracted_query, embedding)
    else:
        # Path 3: MISS - May rewrite for follow-ups
        handler_result = _handle_cache_miss(full_query, extracted_query)

    # Merge base state with handler result
    return {**base_state, **handler_result}
