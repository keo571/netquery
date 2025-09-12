"""
SQL generator node for Text-to-SQL pipeline.
Generates SQL queries from natural language using LLM.
"""
from typing import Dict, Any
import logging
import time

from ...config import config
from ..state import TextToSQLState
from ...utils.sql_utils import extract_sql_from_response, format_sql_query
from ...prompts.sql_generation import SQL_GENERATION_PROMPT
from ...utils.llm_utils import get_llm

logger = logging.getLogger(__name__)


def sql_generator_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Generate SQL query from natural language using LLM with schema context.
    
    This node:
    1. Uses the query plan and schema context to generate SQL
    2. Applies best practices and optimization hints
    3. Includes explanation of the generated query
    4. Provides confidence score for the generation
    """
    # Get validated inputs from previous nodes
    query = state["original_query"]  # From initial state
    schema_context = state["schema_context"]  # From schema_analyzer
    query_plan = state["query_plan"]  # From query_planner
    
    
    logger.info(f"Generating SQL for query: {query[:100]}...")
    
    # Measure SQL generation time
    start_time = time.time()
    
    # Get shared LLM instance
    llm = get_llm()
    
    # Create SQL generation prompt
    sql_prompt = _create_sql_generation_prompt(
        query, schema_context, query_plan
    )
    
    # Generate SQL
    response = llm.invoke(sql_prompt)
    response_text = response.content.strip()
    
    sql_generation_time_ms = (time.time() - start_time) * 1000
    
    try:
        # Extract and clean SQL using utility function
        generated_sql = extract_sql_from_response(response_text)
        
        # Format SQL for readability
        generated_sql = format_sql_query(generated_sql)
        
        logger.info(f"SQL generated successfully")
        
        # Log the reasoning step
        reasoning_step = {
            "step_name": "SQL Generation",
            "details": "Successfully generated the SQL query based on the plan and schema.",
            "status": "✅"
        }
        
        return {
            "generated_sql": generated_sql,
            "sql_generation_time_ms": sql_generation_time_ms,
            "reasoning_log": [reasoning_step]
        }
        
    except ValueError as e:
        logger.error(f"Failed to extract SQL from LLM response: {e}")
        logger.debug(f"LLM response was: {response_text}")
        
        # Log the reasoning step for failure
        reasoning_step = {
            "step_name": "SQL Generation",
            "details": f"Failed to extract valid SQL from the LLM response: {str(e)}",
            "status": "❌"
        }
        
        return {
            "generated_sql": "",
            "generation_error": f"Could not generate valid SQL: {str(e)}",
            "reasoning_log": [reasoning_step]
        }


def _create_sql_generation_prompt(query: str, schema_context: str, 
                                query_plan: Dict[str, Any]) -> str:
    """Create the SQL generation prompt for the LLM."""
    
    # Use the prompt template with structured query plan
    return SQL_GENERATION_PROMPT.format(
        schema_context=schema_context,
        query_plan=query_plan,
        query=query
    )


