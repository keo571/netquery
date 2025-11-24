"""
Cache lookup node - checks for cached SQL before expensive pipeline processing.

This node checks if we have cached SQL for the query.
If we have cached SQL, we can skip the entire pipeline (schema analysis + SQL generation).

Performance Impact:
- Cache HIT: Skip to validator (~1-10ms vs ~2-3 seconds)
- Cache MISS: Continue to normal pipeline flow

Follow-up Question Handling:
- Cache HIT: Use cached SQL directly (no rewriting needed)
- Cache MISS: Rewrite follow-up to standalone query for accurate table selection
"""
import logging
from typing import Dict, Any
from ..state import TextToSQLState, create_success_step
from ...utils.query_rewriter import rewrite_if_needed
from ....api.app_context import AppContext

logger = logging.getLogger(__name__)


def cache_lookup_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Check SQL cache for previously generated SQL.

    Flow:
    1. Get extracted query and sql_query (if rewritten by intent classifier)
    2. Check cache with the query
    3. Route based on cache result:
       - HIT  → Return cached SQL (skip to validator)
       - MISS → Rewrite if needed, continue to schema analyzer

    Performance:
    - Cache hit: ~1-10ms (skip entire pipeline)
    - Cache miss: Continue to schema analyzer (~2.5s)

    Returns:
        State updates with cache results
    """
    # Extract queries from state
    full_query = state["original_query"]
    extracted_query = state["extracted_query"]
    sql_query = state.get("sql_query")
    query_to_cache = sql_query or extracted_query

    # Check cache
    sql_cache = AppContext.get_instance().get_sql_cache()
    cached_sql = sql_cache.get(query_to_cache)

    # Build result based on cache hit/miss
    result = {"sql_cache": sql_cache}

    if cached_sql:
        result.update(_handle_cache_hit(cached_sql, query_to_cache))
    else:
        result.update(_handle_cache_miss(full_query, extracted_query, sql_query))

    return result


def _handle_cache_hit(cached_sql: str, query_to_cache: str) -> Dict[str, Any]:
    """
    Handle cache hit: return cached SQL and skip pipeline.

    Args:
        cached_sql: The SQL retrieved from cache
        query_to_cache: The query that was used for cache lookup

    Returns:
        State updates for cache hit
    """
    logger.info("🚀 Cache HIT - returning cached SQL (~2-3s saved)")

    return {
        "cached_sql": cached_sql,
        "generated_sql": cached_sql,
        "query_for_embedding": query_to_cache,
        "cache_hit_type": "full",
        "reasoning_log": [create_success_step(
            "Cache Lookup",
            "Cache HIT - retrieved SQL from cache. "
            "Skipped schema analysis and SQL generation (~2-3 seconds saved)."
        )]
    }


def _handle_cache_miss(full_query: str, extracted_query: str, sql_query: str = None) -> Dict[str, Any]:
    """
    Handle cache miss: rewrite query if needed for embedding.

    Args:
        full_query: Original full user query
        extracted_query: SQL-relevant part extracted by intent classifier
        sql_query: Pre-rewritten query from intent classifier (for mixed queries)

    Returns:
        State updates for cache miss with rewritten query
    """
    logger.info("Cache MISS - will generate SQL from scratch")

    # Determine query for embedding and rewrite note
    if sql_query:
        # Already rewritten by intent classifier
        query_for_embedding = sql_query
        rewrite_note = " Using clarified SQL query from intent classification."
        logger.info("Cache MISS - using query from intent classification")
    else:
        # Rewrite follow-ups for accurate table selection
        query_for_embedding = rewrite_if_needed(full_query, extracted_query)

        if query_for_embedding != extracted_query:
            rewrite_note = " Rewrote follow-up query for accurate table selection."
            logger.info("Cache MISS - follow-up detected, rewriting for table selection")
        else:
            rewrite_note = ""

    return {
        "query_for_embedding": query_for_embedding,
        "reasoning_log": [create_success_step(
            "Cache Lookup",
            f"Cache MISS - will generate embedding and SQL from scratch.{rewrite_note}"
        )]
    }
