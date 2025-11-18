"""
Query triage node - filters out non-database questions before expensive pipeline processing.

This node uses simple heuristics to quickly identify obvious non-queries like:
- Definition requests: "What is a load balancer?"
- Explanatory questions: "How does DNS work?"
- General knowledge: "Who invented SQL?"

Benefits:
- Saves API costs (no embedding/LLM calls for non-queries)
- Faster response (~1ms vs 2-3 seconds)
- Better UX (helpful message vs confusing SQL error)
"""
import re
import logging
from typing import Dict, Any
from ..state import TextToSQLState
from ....common.schema_summary import get_schema_overview, _resolve_schema_path

logger = logging.getLogger(__name__)


def is_database_query(query: str) -> tuple[bool, str]:
    """
    Use heuristics to determine if query is asking for database data.

    Args:
        query: User's natural language query

    Returns:
        Tuple of (is_db_query: bool, reason: str)
    """
    query_lower = query.lower().strip()

    # Pattern 1: Definition/explanation requests
    # "What is X?", "Who is X?", "Explain X", "Define X"
    definition_patterns = [
        r"^what (?:is|are|was|were) (?:a |an |the )?(\w+)",
        r"^who (?:is|are|was|were) ",
        r"^explain ",
        r"^define ",
        r"^what does .+ mean",
        r"^tell me about ",
    ]

    for pattern in definition_patterns:
        match = re.search(pattern, query_lower)
        if match:
            # Special cases that ARE queries despite matching definition patterns
            # "how many"/"how much" are always queries
            if "how many" in query_lower or "how much" in query_lower:
                continue

            # "what are the [oldest/newest/latest/top/etc]" are queries about data
            query_modifiers = ["oldest", "newest", "latest", "recent", "top", "bottom",
                             "first", "last", "best", "worst", "highest", "lowest"]
            if any(f"what are the {mod}" in query_lower or f"what is the {mod}" in query_lower
                   for mod in query_modifiers):
                continue

            return False, f"Detected definition/explanation request: pattern '{pattern}'"

    # Pattern 2: Process/mechanism questions
    # "How does X work?", "Why does X happen?"
    mechanism_patterns = [
        r"^how (?:does|do|did) .+ work",
        r"^why (?:does|do|did|is|are) ",
        r"^who (?:invented|created|made|developed)",
    ]

    for pattern in mechanism_patterns:
        if re.search(pattern, query_lower):
            # Exception: "why is X empty" could be a data question
            if "empty" not in query_lower and "missing" not in query_lower and "null" not in query_lower:
                return False, f"Detected mechanism/process question: pattern '{pattern}'"

    # Pattern 3: Database query indicators (strong signals)
    query_indicators = [
        "show", "list", "display", "get", "find", "fetch",
        "count", "how many", "how much",
        "all", "total", "sum", "average", "max", "min",
        "recent", "latest", "newest", "oldest",
        "where", "when", "which",
        "unhealthy", "healthy", "failed", "success",
        "top", "bottom", "first", "last",
    ]

    has_query_indicator = any(indicator in query_lower for indicator in query_indicators)

    # If we see database keywords, it's likely a query
    # BUT check for "show me what X is" pattern - that's asking for definition, not data
    if has_query_indicator:
        # Pattern: "show/tell/explain me what [something] is/means"
        if re.search(r"(?:show|tell|explain) me what .+ (?:is|are|means)", query_lower):
            return False, "Detected definition request disguised as query"
        return True, "Contains database query indicators"

    # Default: assume it's a database query (permissive approach)
    # Better to occasionally process a non-query than to reject valid queries
    return True, "No clear non-query patterns detected (default to query)"


def triage_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Triage node - quick filter before expensive pipeline processing.

    Checks if the query is asking for database data or is a general question.
    Routes non-queries to a helpful error response immediately.
    """
    query = state["original_query"]

    is_query, reason = is_database_query(query)

    if not is_query:
        logger.info(f"🚫 Query triaged as non-database question: '{query}' | Reason: {reason}")

        # Get schema overview for helpful suggestions
        # Resolve canonical schema path
        resolved_path = _resolve_schema_path(state.get("canonical_schema_path"))
        canonical_schema_path = str(resolved_path) if resolved_path else None
        schema_overview = get_schema_overview(canonical_schema_path)

        # Build helpful response - don't duplicate schema/queries since frontend displays them separately
        response = (
            "I'm great at SQL, but not so great at general knowledge!\n\n"
            "Your question seems to be asking for definitions rather than database queries. "
            "Try asking about the datasets below instead."
        )

        return {
            "triage_passed": False,
            "final_response": response,
            "execution_error": f"Non-database question: {reason}",
            "schema_overview": schema_overview  # Frontend will display this separately
        }

    logger.info(f"✅ Triage passed | {reason}")

    return {
        "triage_passed": True
    }
