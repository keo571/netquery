"""
Query extraction utilities for handling conversation context.

This module extracts the actual current query from conversation context
sent by the frontend chat adapter, which includes conversation history.
"""
import re
import logging

logger = logging.getLogger(__name__)


def extract_current_query(full_query: str) -> str:
    """
    Extract the actual current query from conversation context.

    The frontend chat adapter (BFF layer) sends queries with conversation history:

    Format from chat_adapter.py build_context_prompt():
    ```
    CONVERSATION HISTORY - Use this to understand follow-up questions:

    Exchange 1:
      User asked: Show me all servers
      SQL query: SELECT * FROM servers

    USER'S NEW QUESTION: which ones are unhealthy?

    CONTEXT RULES FOR FOLLOW-UP QUESTIONS:
    ...
    ```

    This function extracts just "which ones are unhealthy?" for cache matching.

    Args:
        full_query: Full query string (may include conversation context)

    Returns:
        Extracted current query (or full query if no context detected)

    Examples:
        >>> extract_current_query("Show me all servers")
        "Show me all servers"

        >>> extract_current_query('''
        ... CONVERSATION HISTORY - Use this to understand follow-up questions:
        ... Exchange 1:
        ...   User asked: Show servers
        ...   SQL query: SELECT * FROM servers
        ... USER'S NEW QUESTION: which are unhealthy?
        ... ''')
        "which are unhealthy?"
    """
    # Extract query using "USER'S NEW QUESTION:" marker from chat adapter
    match = re.search(
        r"USER'S\s+NEW\s+QUESTION:\s*(.+?)(?:\n\s*CONTEXT\s+RULES|\n\s*$)",
        full_query,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        current_query = match.group(1).strip()
        logger.debug(f"Extracted query from conversation context ({len(full_query)} → {len(current_query)} chars)")
        return current_query

    # No context marker found - return full query as-is
    # This is normal for first queries in a conversation
    logger.debug(f"No context markers found, using full query: '{full_query[:60]}...'")
    return full_query.strip()


