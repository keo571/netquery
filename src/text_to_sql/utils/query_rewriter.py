"""
Query rewriter for converting follow-up questions into standalone queries.

This module handles:
1. Intent classification (sql/general/mixed) using LLM with JSON output
2. Rewriting of ambiguous follow-up questions into self-contained queries

Example:
    User asks: "Show me all servers"
    User follows up: "which ones are unhealthy?"

    Rewriter output: "Show me all unhealthy servers"
"""
import json
import logging
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from ...common.config import config
from ..utils.llm_utils import get_llm

logger = logging.getLogger(__name__)


def cleanup_json_response(text: str) -> str:
    """
    Clean LLM response to extract valid JSON.

    Handles:
    - Markdown code blocks (```json ... ```)
    - Extra text before/after JSON
    - Whitespace and formatting issues

    Returns:
        Cleaned JSON string ready for parsing
    """
    # Remove markdown code blocks (```json or just ```)
    text = re.sub(r'```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)

    # Find JSON object (in case LLM adds extra text)
    # Look for outermost { ... }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0).strip()

    return text.strip()


@dataclass
class IntentClassification:
    """Result of intent classification."""
    intent: str  # "sql", "general", or "mixed"
    sql_query: Optional[str] = None  # Rewritten SQL-relevant query (for sql/mixed)
    general_answer: Optional[str] = None  # Direct answer for general questions


def _is_obvious_sql_query(query: str) -> bool:
    """
    Fast heuristic to detect obvious SQL-intent queries without LLM.

    Returns True ONLY for queries that are unambiguously asking for data.
    Conservative approach: Only match clear data request patterns.

    This saves ~200ms by skipping the LLM call for obvious cases.
    """
    query_lower = query.lower().strip()
    words = query_lower.split()

    if len(words) < 2:
        return False

    # Question words that indicate NOT a data request
    question_words = {'how', 'why', 'what', 'when', 'where', 'who'}

    # Clear SQL action patterns with articles (unambiguous)
    sql_start_patterns = [
        'show all ', 'show the ',
        'list all ', 'list the ',
        'get all ', 'get the ',
        'find all ', 'find the ',
        'display all ', 'display the ',
        'count all ', 'count the ',
        'give me all ', 'give me the ',
        'fetch all ', 'fetch the ',
    ]

    for pattern in sql_start_patterns:
        if query_lower.startswith(pattern):
            return True

    # Check action verbs: show, list, get, find, display, count
    action_verbs = {'show', 'list', 'get', 'find', 'display', 'count'}
    first_word = words[0]

    if first_word not in action_verbs:
        # Special case: "how many X" is clearly asking for data count
        if query_lower.startswith('how many '):
            return True
        return False

    # Handle "verb me X" pattern (e.g., "show me servers")
    second_word = words[1]
    if second_word == 'me':
        if len(words) > 2:
            third_word = words[2]
            return third_word not in question_words
        return False

    # Handle "verb X" pattern (e.g., "show servers")
    return second_word not in question_words


def classify_intent(query: str, full_query: str = None, schema_summary: str = "") -> IntentClassification:
    """
    Classify query intent using heuristics first, then LLM as fallback.

    Determines if a query is:
    - "sql": Requires database query (e.g., "List all servers")
    - "general": General knowledge question (e.g., "What is a load balancer?")
    - "mixed": Contains both (e.g., "What is DNS? Show all DNS records")

    Performance optimization:
    - Uses fast heuristics (~1ms) for obvious SQL queries
    - Falls back to LLM (~200ms) for ambiguous cases and general questions

    Args:
        query: The extracted user's query
        full_query: Optional full query with conversation context
        schema_summary: Optional schema context to help LLM understand what's in the DB

    Returns:
        IntentClassification with intent type and appropriate responses
    """
    # ================================================================
    # Fast-path: Use heuristics for obvious SQL queries (~1ms vs ~200ms LLM)
    # Only skip LLM for unambiguous data requests
    # ================================================================

    # Check for obvious SQL queries (conservative matching)
    if _is_obvious_sql_query(query):
        logger.info(f"⚡ Fast-path: Obvious SQL query detected (skipped LLM)")
        return IntentClassification(intent="sql", sql_query=query)

    # ================================================================
    # Slow-path: Use LLM for all other cases (general, mixed, ambiguous)
    # ================================================================
    # Build dynamic domain scope from schema
    schema_context = ""
    domain_scope_section = ""
    if schema_summary:
        schema_context = f"\n\nAVAILABLE DATABASE TABLES:\n{schema_summary}"
        # Dynamic domain scope based on actual schema
        domain_scope_section = """
DOMAIN SCOPE: This system answers questions about NETWORK INFRASTRUCTURE data in the database.
Questions must be about the tables and data shown above."""
    else:
        # Fallback to generic network infrastructure scope if no schema available
        domain_scope_section = """
DOMAIN SCOPE: This system answers questions about NETWORK INFRASTRUCTURE ONLY.
Topics include: network devices, traffic, performance, health monitoring, and configuration."""

    # Extract conversation history if available
    conversation_context = ""
    if full_query and "CONVERSATION HISTORY" in full_query:
        history_lines = []
        for line in full_query.split('\n'):
            if 'User asked:' in line:
                prev_question = line.split('User asked:')[1].strip()
                history_lines.append(f"- {prev_question}")

        if history_lines:
            conversation_context = f"\n\nPrevious questions in this conversation:\n" + "\n".join(history_lines)

    prompt = f"""You are a network infrastructure AI assistant analyzing user queries.{schema_context}{conversation_context}

Current query: "{query}"

{domain_scope_section}

OUT-OF-SCOPE TOPICS (must reject):
- Gardening, cooking, sports, entertainment, travel, shopping
- General life advice, weather, news, finance, medical topics
- Programming languages, non-network software, mobile apps
- Any topic unrelated to network infrastructure

CRITICAL: Your response must be ONLY valid JSON. No markdown, no explanations, no code blocks.

Classification rules:
- "sql": Query asks for data from database (list, count, show, find, get records) AND is about network infrastructure
- "general": Query asks for networking/infrastructure explanation (what is load balancer, how does BGP work)
- "mixed": Query contains BOTH a general networking question AND a database query
- "out_of_scope": Query is NOT about network infrastructure (gardening, cooking, etc.) - REJECT these

IMPORTANT: For out-of-scope queries:
- Set intent to "general"
- Provide a polite rejection in general_answer explaining this is a network infrastructure assistant
- Set sql_query to null

For sql_query field, you MUST:
1. For standalone queries: Use the query as-is
2. For follow-up queries: Rewrite into a complete standalone query using conversation context
3. ALWAYS provide sql_query for "sql" and "mixed" intents (never null)
4. For out-of-scope queries: Set to null

Your response must be a single JSON object:
{{"intent": "sql", "sql_query": "...", "general_answer": null}}

Examples:
IN-SCOPE (accept):
- "Show all servers" → {{"intent": "sql", "sql_query": "Show all servers", "general_answer": null}}
- "which are unhealthy?" (follow-up) → {{"intent": "sql", "sql_query": "Show all unhealthy servers", "general_answer": null}}
- "What is a load balancer?" → {{"intent": "general", "sql_query": null, "general_answer": "A load balancer distributes network traffic..."}}
- "What is BGP? Show BGP routes" → {{"intent": "mixed", "sql_query": "Show BGP routes", "general_answer": "BGP is..."}}

OUT-OF-SCOPE (reject):
- "I need help with gardening" → {{"intent": "general", "sql_query": null, "general_answer": "I'm a network infrastructure assistant and can only help with questions about the network infrastructure data in the database. I cannot help with gardening topics."}}
- "deal with pests" (after gardening question) → {{"intent": "general", "sql_query": null, "general_answer": "I can only assist with network infrastructure topics related to the database. For gardening help, please consult a gardening expert or resource."}}
- "What's the weather?" → {{"intent": "general", "sql_query": null, "general_answer": "I'm a network infrastructure assistant. I can help you query the network infrastructure data in the database."}}

For mixed queries: extract the data request into sql_query, answer the knowledge part in general_answer.
For sql queries: ALWAYS rewrite follow-ups into standalone queries, set general_answer to null.
For general IN-SCOPE queries: provide helpful networking answer, set sql_query to null.
For OUT-OF-SCOPE queries: politely reject and explain scope, set sql_query to null.

JSON response:"""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        response_text = response.content.strip()

        # Clean up response (remove markdown, extract JSON)
        cleaned_text = cleanup_json_response(response_text)

        result = json.loads(cleaned_text)

        intent = result.get("intent", "sql").lower()
        if intent not in ("sql", "general", "mixed"):
            intent = "sql"  # Default to sql for safety

        classification = IntentClassification(
            intent=intent,
            sql_query=result.get("sql_query"),
            general_answer=result.get("general_answer")
        )

        logger.info(f"Intent classification: {intent} for query: '{query[:50]}...'")
        return classification

    except json.JSONDecodeError as e:
        logger.warning(
            f"Failed to parse intent JSON, defaulting to sql.\n"
            f"Error: {e}\n"
            f"Raw response: {response_text[:200]}..."
        )
        # Default to treating as SQL query
        return IntentClassification(intent="sql", sql_query=query)
    except Exception as e:
        logger.warning(f"Intent classification failed, defaulting to sql: {e}")
        return IntentClassification(intent="sql", sql_query=query)
