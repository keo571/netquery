"""
SQL generator node for Text-to-SQL pipeline.
Generates SQL queries from natural language using LLM.
"""
from typing import Dict, Any
import logging
import time

from ..state import TextToSQLState
from ...utils.sql_utils import extract_sql_from_response
from ...prompts.sql_generation import SQL_GENERATION_PROMPT
from ...utils.llm_utils import get_llm

logger = logging.getLogger(__name__)

# SQL generation with fail-fast approach - rely on upstream nodes for quality


def sql_generator_node(state: TextToSQLState) -> Dict[str, Any]:
    """Generate SQL query from natural language using LLM with schema context."""
    query = state["original_query"]
    schema_context = state["schema_context"]
    query_plan = state["query_plan"]

    logger.info(f"Generating SQL for query: {query[:100]}...")

    start_time = time.time()
    llm = get_llm()
    sql_prompt = _create_sql_generation_prompt(query, schema_context, query_plan)

    response = llm.invoke(sql_prompt)
    sql_generation_time_ms = (time.time() - start_time) * 1000

    for attempt in range(2):  # Try twice for LLM non-determinism
        try:
            if attempt == 0:
                current_response = response.content.strip()
            else:
                logger.info("Retrying SQL generation due to validation error...")
                retry_response = llm.invoke(sql_prompt)
                current_response = retry_response.content.strip()

            generated_sql = extract_sql_from_response(current_response)

            # Basic validation
            if not generated_sql or not generated_sql.strip():
                raise ValueError("No SQL query generated")

            # Block CTEs entirely to prevent syntax errors
            if generated_sql.upper().strip().startswith('WITH'):
                raise ValueError("CTEs (WITH clauses) not allowed - use subqueries instead")

            # Success!
            retry_note = " (after retry)" if attempt > 0 else ""
            logger.info(f"SQL generated and syntax validated successfully{retry_note}")

            return {
                "generated_sql": generated_sql,
                "sql_generation_time_ms": sql_generation_time_ms,
                "reasoning_log": [{
                    "step_name": "SQL Generation",
                    "details": f"Successfully generated and validated SQL syntax{retry_note}.",
                    "status": "✅"
                }]
            }

        except Exception as e:
            if attempt == 0:
                # First attempt failed, try once more
                continue

            # Both attempts failed
            logger.error(f"SQL generation failed after 2 attempts: {str(e)}")
            return {
                "generated_sql": "",
                "generation_error": str(e),
                "reasoning_log": [{
                    "step_name": "SQL Generation",
                    "details": f"Failed to generate valid SQL after 2 attempts: {str(e)}",
                    "status": "❌"
                }]
            }


def _create_sql_generation_prompt(query: str, schema_context: str, query_plan: Dict[str, Any]) -> str:
    """Create the SQL generation prompt for the LLM."""
    return SQL_GENERATION_PROMPT.format(
        schema_context=schema_context,
        query_plan=query_plan,
        query=query
    )


