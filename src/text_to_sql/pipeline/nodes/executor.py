"""
Executor node for Text-to-SQL pipeline.
Executes validated SQL queries against the database using SQLAlchemy.
"""
from typing import Dict, Any
import logging

from ...tools.database_toolkit import db_toolkit
from ...config import config
from ..state import TextToSQLState

logger = logging.getLogger(__name__)


def executor_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Execute the validated SQL query against the database.
    
    This node:
    1. Executes the SQL query safely
    2. Handles execution errors gracefully
    3. Formats results appropriately
    4. Records execution metadata
    """
    try:
        generated_sql = state.get("generated_sql", "")
        is_valid = state.get("is_valid", False)
        
        if not generated_sql:
            return {
                "query_results": None,
                "execution_time_ms": None,
                "rows_affected": 0,
                "execution_error": "No SQL query provided for execution"
            }
        
        if not is_valid:
            return {
                "query_results": None,
                "execution_time_ms": None,
                "rows_affected": 0,
                "execution_error": "SQL query failed validation and cannot be executed"
            }
        
        logger.info(f"Executing SQL query: {generated_sql[:100]}...")
        
        # Execute the query using SQLAlchemy toolkit
        execution_result = db_toolkit.execute_query(generated_sql)
        
        if execution_result["success"]:
            query_results = execution_result["data"]
            execution_time_ms = execution_result["execution_time_ms"]
            rows_affected = execution_result["row_count"]
            execution_error = None
            
            # Log successful execution
            logger.info(f"Query executed successfully: {rows_affected} rows returned in {execution_time_ms:.2f}ms")
            
            # Check if results were truncated
            if execution_result.get("truncated", False):
                logger.warning(f"Results truncated to {config.safety.max_result_rows} rows")
        else:
            query_results = None
            execution_time_ms = execution_result["execution_time_ms"]
            rows_affected = 0
            execution_error = execution_result["error"]
            
            logger.error(f"Query execution failed: {execution_error}")
        
        # Log the reasoning step
        if execution_error:
            details = f"Query execution failed. Error: {execution_error}"
            status = "❌"
        else:
            details = f"Successfully executed the query, retrieving {rows_affected} rows in {execution_time_ms:.0f}ms."
            status = "✅"
            
        reasoning_step = {
            "step_name": "Execution",
            "details": details,
            "status": status
        }

        return {
            "query_results": query_results,
            "execution_time_ms": execution_time_ms,
            "rows_affected": rows_affected,
            "execution_error": execution_error,
            "reasoning_log": [reasoning_step]
        }
        
    except Exception as e:
        logger.error(f"SQL execution failed: {str(e)}")
        return {
            "query_results": None,
            "execution_time_ms": None,
            "rows_affected": 0,
            "execution_error": f"Execution error: {str(e)}"
        }