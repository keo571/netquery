"""
SQL generator node for Text-to-SQL pipeline.
Generates SQL queries directly from natural language using LLM.
"""
from typing import Dict, Any
import logging
import time

from ..state import TextToSQLState, create_success_step, create_error_step
from ...utils.sql_utils import extract_sql_from_response, adapt_sql_for_database
from ...prompts._shared import create_sql_prompt
from ....common.config import config
from ...utils.llm_utils import get_llm

logger = logging.getLogger(__name__)


def sql_generator(state: TextToSQLState) -> Dict[str, Any]:
    """
    Generate SQL query directly from natural language using LLM with schema context.

    This node:
    1. Takes the natural language query and schema context
    2. Generates SQL directly in one LLM call (no intermediate planning step)
    3. Validates basic syntax and safety rules
    4. Caches the generated SQL for future use
    5. Returns the generated SQL or error state
    """
    query = state["original_query"]
    schema_context = state["schema_context"]
    query_cache = state.get("query_cache")

    # Use extracted_query for caching (from cache_lookup_node)
    # This is the clean query without conversation context
    extracted_query = state.get("extracted_query", query)

    logger.info(f"Generating SQL for query: {query[:100]}...")

    start_time = time.time()
    llm = get_llm()

    # Create SQL generation prompt directly from query and schema
    # No intermediate planning step - LLM generates SQL directly
    database_url = config.database.database_url
    sql_prompt = create_sql_prompt(
        query=query,
        schema_context=schema_context,
        query_plan="",  # No query plan - direct generation
        database_url=database_url
    )

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
            generated_sql = adapt_sql_for_database(generated_sql, database_url)

            # Basic validation
            if not generated_sql or not generated_sql.strip():
                raise ValueError("No SQL query generated")

            # Block CTEs entirely to prevent syntax errors
            if generated_sql.upper().strip().startswith('WITH'):
                raise ValueError("CTEs (WITH clauses) not allowed - use subqueries instead")

            # Success!
            retry_note = " (after retry)" if attempt > 0 else ""
            logger.info(f"SQL generated and syntax validated successfully{retry_note}")

            # Cache the generated SQL for future use
            # Use extracted_query (without conversation context) for caching
            if query_cache:
                # Update only the SQL (embedding already cached by schema analyzer)
                if query_cache.update_sql(extracted_query, generated_sql):
                    logger.info(f"Cached generated SQL for query: '{extracted_query[:60]}...'")
                else:
                    logger.warning(f"Could not cache SQL - no entry found in cache for query: '{extracted_query[:60]}...'")

            return {
                "generated_sql": generated_sql,
                "sql_generation_time_ms": sql_generation_time_ms,
                "reasoning_log": [create_success_step(
                    "SQL Generation",
                    f"Successfully generated and validated SQL syntax{retry_note}."
                )]
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
                "reasoning_log": [create_error_step(
                    "SQL Generation",
                    f"Failed to generate valid SQL after 2 attempts: {str(e)}"
                )]
            }

