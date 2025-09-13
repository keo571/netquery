"""
Executor node for Text-to-SQL pipeline.
Executes validated SQL queries against the database using SQLAlchemy.
"""
from typing import Dict, Any
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

from ...tools.database_toolkit import db_toolkit
from ..state import TextToSQLState

logger = logging.getLogger(__name__)


def executor_node(state: TextToSQLState) -> Dict[str, Any]:
    """Execute the validated SQL query against the database."""
    generated_sql = state["generated_sql"]
    logger.info(f"Executing SQL query: {generated_sql[:100]}...")
    
    # Execute query
    execution_result = db_toolkit.execute_query(generated_sql)
    
    if execution_result["success"]:
        query_results = execution_result["data"]
        execution_time_ms = execution_result["execution_time_ms"]
        rows_affected = execution_result["row_count"]
        execution_error = None
        
        # Save all results to CSV if enabled
        csv_path = None
        if state.get("save_csv", False):  # Default to False
            csv_path = _save_results_to_csv(query_results, state["original_query"])
            
        logger.info(f"Query executed: {rows_affected} rows")
    else:
        query_results = None
        execution_time_ms = execution_result["execution_time_ms"]
        rows_affected = 0
        execution_error = execution_result["error"]
        csv_path = None
        logger.error(f"Query execution failed: {execution_error}")
    
    # Reasoning step
    status = "✅" if not execution_error else "❌"
    details = (f"Successfully executed the query, retrieving {rows_affected} rows in {execution_time_ms:.0f}ms." 
              if not execution_error else f"Query execution failed. Error: {execution_error}")
    
    return {
        "query_results": query_results,
        "execution_time_ms": execution_time_ms,
        "rows_affected": rows_affected,
        "execution_error": execution_error,
        "csv_export_path": csv_path,
        "reasoning_log": [{
            "step_name": "Execution",
            "details": details,
            "status": status
        }]
    }


def _save_results_to_csv(data: list, query: str) -> str:
    """Save query results to CSV."""
    if not data:
        return None
        
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_id = abs(hash(query)) % 10000
        filename = f"query_{query_id}_{timestamp}.csv"
        
        Path("outputs/query_data").mkdir(parents=True, exist_ok=True)
        filepath = f"outputs/query_data/{filename}"
        
        pd.DataFrame(data).to_csv(filepath, index=False)
        return filepath
    except Exception as e:
        logger.error(f"CSV save failed: {e}")
        return None
