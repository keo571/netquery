"""
Query rewriter for converting follow-up questions into standalone queries.

This module handles the rewriting of ambiguous follow-up questions into
self-contained queries that can be properly embedded for table selection.

Example:
    User asks: "Show me all servers"
    User follows up: "which ones are unhealthy?"

    Rewriter output: "Show me all unhealthy servers"
"""
import logging
import re
from typing import Optional
from ...common.config import config
from ..utils.llm_utils import get_llm

logger = logging.getLogger(__name__)


def needs_rewriting(full_query: str, extracted_query: str) -> bool:
    """
    Determine if a query needs rewriting.

    A query needs rewriting if:
    1. It has conversation history (is a follow-up)
    2. The extracted query is ambiguous (has pronouns, missing context)

    Args:
        full_query: Full query with conversation context
        extracted_query: Extracted current question

    Returns:
        True if rewriting is recommended
    """
    # Check if this is a follow-up question (has conversation history)
    has_history = "CONVERSATION HISTORY" in full_query or "USER'S NEW QUESTION" in full_query

    if not has_history:
        return False

    # Check for ambiguous patterns in extracted query
    ambiguous_patterns = [
        r'\b(which|those|these|them|they|it|its)\b',  # Pronouns
        r'\b(more|other|also|too)\b',  # Continuation words
        r'^(and|or|but)\b',  # Starting with conjunctions
        r'\?$',  # Questions without clear subject
    ]

    extracted_lower = extracted_query.lower()
    for pattern in ambiguous_patterns:
        if re.search(pattern, extracted_lower):
            logger.info(
                f"Detected ambiguous follow-up query: '{extracted_query[:60]}...' "
                f"(matched pattern: {pattern})"
            )
            return True

    return False


def rewrite_follow_up_query(full_query: str, extracted_query: str) -> str:
    """
    Rewrite a follow-up question into a standalone query using LLM.

    This function takes a follow-up question with conversation context and
    rewrites it into a self-contained question that includes all necessary context.

    Args:
        full_query: Full query string with conversation history
        extracted_query: The current follow-up question

    Returns:
        Rewritten standalone query

    Example:
        Input:
            full_query = '''
            CONVERSATION HISTORY:
            Exchange 1:
              User asked: Show me all servers
              SQL query: SELECT * FROM servers
            USER'S NEW QUESTION: which ones are unhealthy?
            '''
            extracted_query = "which ones are unhealthy?"

        Output:
            "Show me all unhealthy servers"
    """
    # Extract conversation history for context
    history_lines = []
    for line in full_query.split('\n'):
        if 'User asked:' in line:
            prev_question = line.split('User asked:')[1].strip()
            history_lines.append(f"Previous: {prev_question}")

    context = "\n".join(history_lines) if history_lines else "No previous context"

    # Create rewriting prompt
    prompt = f"""You are a query rewriter. Rewrite the follow-up question into a complete, standalone question.

{context}

Follow-up question: {extracted_query}

Instructions:
- Rewrite the follow-up question to be self-contained
- Include context from the previous question
- Keep it concise (one sentence)
- Do not add new requirements not in the follow-up
- Output ONLY the rewritten question, nothing else

Rewritten question:"""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        rewritten = response.content.strip()

        # Clean up common LLM artifacts
        rewritten = rewritten.strip('"\'')  # Remove quotes
        rewritten = rewritten.split('\n')[0]  # Take first line only

        logger.info(
            f"Rewrote follow-up query:\n"
            f"  Original: '{extracted_query}'\n"
            f"  Rewritten: '{rewritten}'"
        )

        return rewritten

    except Exception as e:
        logger.warning(
            f"Failed to rewrite query, using original: {e}\n"
            f"  Query: '{extracted_query}'"
        )
        # Fallback: return original extracted query
        return extracted_query


def rewrite_if_needed(
    full_query: str,
    extracted_query: str,
    cache_hit_type: Optional[str] = None
) -> str:
    """
    Conditionally rewrite query only if needed.

    Optimization: Skip rewriting if we have a full cache hit (have SQL).
    Only rewrite for cache MISS or PARTIAL hit (need table selection).

    Args:
        full_query: Full query with conversation context
        extracted_query: Extracted current question
        cache_hit_type: 'full', 'partial', or None

    Returns:
        Rewritten query if needed, otherwise original extracted_query
    """
    # Fast path: Full cache hit means we have SQL, no need to rewrite
    if cache_hit_type == 'full':
        logger.debug("Full cache hit - skipping query rewriting")
        return extracted_query

    # Check if rewriting is needed
    if not needs_rewriting(full_query, extracted_query):
        logger.debug("Query does not need rewriting (standalone)")
        return extracted_query

    # Rewrite for accurate table selection
    logger.info("Cache miss/partial for follow-up - rewriting query for accurate table selection")
    return rewrite_follow_up_query(full_query, extracted_query)
