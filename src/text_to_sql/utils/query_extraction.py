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
    # Pattern 1: "USER'S NEW QUESTION:" marker (from chat_adapter.py)
    # This is the primary pattern used by the BFF layer
    match = re.search(
        r"USER'S\s+NEW\s+QUESTION:\s*(.+?)(?:\n\s*CONTEXT\s+RULES|\n\s*$)",
        full_query,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        current_query = match.group(1).strip()
        logger.debug(f"Extracted query from conversation context ({len(full_query)} → {len(current_query)} chars)")
        return current_query

    # Pattern 2: "Current:" marker (alternative format)
    match = re.search(r'current:\s*(.+?)$', full_query, re.IGNORECASE | re.DOTALL)
    if match:
        current_query = match.group(1).strip()
        logger.debug(f"Extracted via 'Current:' marker: '{current_query[:60]}...'")
        return current_query

    # Pattern 3: "Question:" marker (alternative format)
    match = re.search(r'question:\s*(.+?)$', full_query, re.IGNORECASE | re.DOTALL)
    if match:
        current_query = match.group(1).strip()
        logger.debug(f"Extracted via 'Question:' marker: '{current_query[:60]}...'")
        return current_query

    # Pattern 4: Multi-line with "User:" prefix (take last user message)
    if '\n' in full_query and 'User:' in full_query:
        lines = full_query.split('\n')
        user_lines = [l.split('User:', 1)[1].strip() for l in lines if l.strip().startswith('User:')]
        if user_lines:
            current_query = user_lines[-1]
            logger.debug(f"Extracted via 'User:' prefix: '{current_query[:60]}...'")
            return current_query

    # No context markers found - return full query as-is
    # This is normal for first queries in a conversation
    logger.debug(f"No context markers found, using full query: '{full_query[:60]}...'")
    return full_query.strip()


def strip_context_rules(query: str) -> str:
    """
    Remove CONTEXT RULES section if present (for cleaner logging).

    Args:
        query: Query string potentially containing context rules

    Returns:
        Query with context rules removed
    """
    # Remove everything after "CONTEXT RULES FOR FOLLOW-UP QUESTIONS:"
    match = re.search(
        r'(.+?)\s*CONTEXT\s+RULES\s+FOR\s+FOLLOW-UP\s+QUESTIONS:',
        query,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        return match.group(1).strip()

    return query.strip()
