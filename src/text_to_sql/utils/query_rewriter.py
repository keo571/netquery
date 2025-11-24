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


def classify_intent(query: str, full_query: str = None, schema_summary: str = "") -> IntentClassification:
    """
    Classify query intent using LLM with JSON structured output.

    Determines if a query is:
    - "sql": Requires database query (e.g., "List all servers")
    - "general": General knowledge question (e.g., "What is a load balancer?")
    - "mixed": Contains both (e.g., "What is DNS? Show all DNS records")

    Args:
        query: The extracted user's query
        full_query: Optional full query with conversation context
        schema_summary: Optional schema context to help LLM understand what's in the DB

    Returns:
        IntentClassification with intent type and appropriate responses
    """
    schema_context = ""
    if schema_summary:
        schema_context = f"\nAvailable database tables: {schema_summary}"

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

    prompt = f"""You are a network engineer AI assistant analyzing user queries.{schema_context}{conversation_context}

Current query: "{query}"

CRITICAL: Your response must be ONLY valid JSON. No markdown, no explanations, no code blocks.

Classification rules:
- "sql": Query asks for data from database (list, count, show, find, get records)
- "general": Query asks for explanation or knowledge (what is X, how does Y work, explain Z)
- "mixed": Query contains BOTH a general question AND a database query

IMPORTANT: For sql_query field, you MUST:
1. For standalone queries: Use the query as-is
2. For follow-up queries: Rewrite into a complete standalone query using conversation context
3. ALWAYS provide sql_query for "sql" and "mixed" intents (never null)

Your response must be a single JSON object:
{{"intent": "sql", "sql_query": "...", "general_answer": null}}

Examples:
- "Show all servers" → {{"intent": "sql", "sql_query": "Show all servers", "general_answer": null}}
- "which are unhealthy?" (follow-up) → {{"intent": "sql", "sql_query": "Show all unhealthy servers", "general_answer": null}}
- "remove column x" (follow-up) → {{"intent": "sql", "sql_query": "Show all servers excluding column x", "general_answer": null}}
- "What is DNS?" → {{"intent": "general", "sql_query": null, "general_answer": "DNS (Domain Name System) is..."}}
- "What is DNS? Show all DNS records" → {{"intent": "mixed", "sql_query": "Show all DNS records", "general_answer": "DNS is..."}}

For mixed queries: extract the data request into sql_query, answer the knowledge part in general_answer.
For sql queries: ALWAYS rewrite follow-ups into standalone queries, set general_answer to null.
For general queries: provide helpful answer, set sql_query to null.

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
