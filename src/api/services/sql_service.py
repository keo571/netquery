"""
SQL generation service.

Provides the core SQL generation logic used by both /api/generate-sql and /chat endpoints.
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SQLGenerationResult:
    """Result of SQL generation."""
    sql: Optional[str]
    intent: str  # "sql", "general", or "mixed"
    general_answer: Optional[str]
    schema_overview: Optional[Dict[str, Any]]
    error: Optional[str] = None


async def generate_sql(
    query: str,
    text_to_sql_graph,
    get_schema_overview_fn
) -> SQLGenerationResult:
    """
    Generate SQL from natural language query.

    Args:
        query: Natural language query (may include conversation context)
        text_to_sql_graph: The LangGraph pipeline for text-to-SQL
        get_schema_overview_fn: Function to get schema overview on error

    Returns:
        SQLGenerationResult with sql, intent, general_answer, and error info
    """
    try:
        result = await text_to_sql_graph.ainvoke({
            "original_query": query,
            "execute": False,
            "show_explanation": False
        })

        generated_sql = result.get("generated_sql")
        intent = result.get("intent", "sql")
        general_answer = result.get("general_answer")

        # Handle generation failure (but not for general questions)
        if not generated_sql and intent != "general":
            overview = result.get("schema_overview") or get_schema_overview_fn()
            return SQLGenerationResult(
                sql=None,
                intent=intent,
                general_answer=general_answer,
                schema_overview=overview,
                error=result.get("final_response") or "Failed to generate SQL"
            )

        return SQLGenerationResult(
            sql=generated_sql,
            intent=intent,
            general_answer=general_answer,
            schema_overview=None,
            error=None
        )

    except Exception as e:
        logger.error(f"SQL generation error: {e}")
        return SQLGenerationResult(
            sql=None,
            intent="error",
            general_answer=None,
            schema_overview=None,
            error=str(e)
        )
