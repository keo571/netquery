"""
Cache lookup node - checks for cached SQL before expensive pipeline processing.

This node checks if we have cached SQL for the query.
If we have cached SQL, we can skip the entire pipeline (schema analysis + SQL generation).

Performance Impact:
- Cache HIT: Skip to validator (~1-10ms vs ~2-3 seconds)
- Cache MISS: Continue to normal pipeline flow

Query Handling:
- Uses sql_query from intent classifier (already rewritten for follow-ups)
- Fallback to extracted_query if sql_query not provided
"""
import logging
from typing import Dict, Any
from ..state import TextToSQLState, create_success_step
from ....api.app_context import AppContext

logger = logging.getLogger(__name__)


def cache_lookup_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Check SQL cache for previously generated SQL.

    Flow:
    1. Get sql_query from intent classifier (already rewritten for follow-ups)
    2. Fallback to extracted_query if sql_query not provided
    3. Check cache with the query
    4. Route based on cache result:
       - HIT  → Return cached SQL (skip to validator)
       - MISS → Continue to schema analyzer

    Performance:
    - Cache hit: ~1-10ms (skip entire pipeline)
    - Cache miss: Continue to schema analyzer (~2.5s)

    Returns:
        State updates with cache results
    """
    # Get query for cache lookup
    # Intent classifier provides sql_query (rewritten for follow-ups)
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
        result.update(_handle_cache_miss(query_to_cache, sql_query))

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


def _handle_cache_miss(query_for_embedding: str, from_intent_classifier: bool) -> Dict[str, Any]:
    """
    Handle cache miss: use query for table selection.

    Args:
        query_for_embedding: Query to use for semantic table search
        from_intent_classifier: Whether query was rewritten by intent classifier

    Returns:
        State updates for cache miss
    """
    logger.info("Cache MISS - will generate SQL from scratch")

    rewrite_note = " Using rewritten query from intent classifier." if from_intent_classifier else ""

    return {
        "query_for_embedding": query_for_embedding,
        "reasoning_log": [create_success_step(
            "Cache Lookup",
            f"Cache MISS - will generate embedding and SQL from scratch.{rewrite_note}"
        )]
    }
