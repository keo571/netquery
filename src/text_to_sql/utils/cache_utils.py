"""
Utility functions for cache management.

These functions provide convenient access to the SQL cache for
external use (e.g., by the chat adapter BFF layer).
"""
import logging
from ...api.app_context import AppContext

logger = logging.getLogger(__name__)


def _get_sql_cache():
    """Get SQL cache from AppContext."""
    return AppContext.get_instance().get_sql_cache()


def invalidate_query_cache(user_question: str) -> bool:
    """
    Invalidate cached SQL for a user question.

    This should be called when user provides negative feedback (thumbs down)
    to force fresh SQL generation on retry.

    Args:
        user_question: The original user question to invalidate

    Returns:
        True if cache entry was invalidated, False if not found

    Example:
        # User clicks thumbs down in chat UI
        # Chat adapter calls this function
        from src.text_to_sql.utils.cache_utils import invalidate_query_cache

        invalidated = invalidate_query_cache("Show me unhealthy servers")
        if invalidated:
            logger.info("Cache invalidated - next query will generate fresh SQL")
    """
    try:
        cache = _get_sql_cache()
        result = cache.invalidate(user_question)

        if result:
            logger.info(f"✅ Cache invalidated for user feedback: '{user_question[:60]}...'")
        else:
            logger.debug(f"No cache entry to invalidate: '{user_question[:60]}...'")

        return result

    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return False


def clear_all_cache() -> int:
    """
    Clear entire SQL cache.

    Useful for admin/debugging purposes.

    Returns:
        Number of entries deleted
    """
    try:
        cache = _get_sql_cache()
        count = cache.clear()
        logger.info(f"✅ Cleared entire cache: {count} entries deleted")
        return count

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return 0


def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache stats (total entries, total hits, top queries)
    """
    try:
        cache = _get_sql_cache()
        stats = cache.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            'total_entries': 0,
            'total_hits': 0,
            'top_queries': []
        }
