"""
Executor node for Text-to-SQL pipeline.
Executes validated SQL queries against the database using SQLAlchemy.
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from pathlib import Path

from ...tools.database_toolkit import GenericDatabaseToolkit, get_db_toolkit
from ..state import TextToSQLState, create_success_step, create_error_step

logger = logging.getLogger(__name__)


def executor(state: TextToSQLState,
            db_toolkit: Optional[GenericDatabaseToolkit] = None) -> Dict[str, Any]:
    """
    Execute the validated SQL query against the database.

    Args:
        state: Pipeline state
        db_toolkit: Optional database toolkit (uses default if None)

    Returns:
        Execution results
    """
    # Dependency injection: use provided toolkit or get default
    toolkit = db_toolkit or get_db_toolkit()

    generated_sql = state["generated_sql"]
    logger.info(f"Executing SQL query: {generated_sql[:100]}...")

    # Execute query
    execution_result = toolkit.execute_query(generated_sql)
    
    if execution_result["success"]:
        query_results = execution_result["data"]
        execution_time_ms = execution_result["execution_time_ms"]
        rows_affected = execution_result["row_count"]
        execution_error = None
        
        # Save results to CSV if enabled
        csv_path = None
        if state.get("export_csv", False):  # Default to False
            csv_path = _save_results_to_csv(query_results, state["original_query"])
            
        logger.info(f"Query executed: {rows_affected} rows")
    else:
        query_results = None
        execution_time_ms = execution_result["execution_time_ms"]
        rows_affected = 0
        execution_error = execution_result["error"]
        csv_path = None
        logger.error(f"Query execution failed: {execution_error}")
    
    # Create reasoning step using helper
    if not execution_error:
        reasoning_step = create_success_step(
            "Execution",
            f"Successfully executed the query, retrieving {rows_affected} rows in {execution_time_ms:.0f}ms."
        )
    else:
        reasoning_step = create_error_step(
            "Execution",
            f"Query execution failed. Error: {execution_error}"
        )

    return {
        "query_results": query_results,
        "execution_time_ms": execution_time_ms,
        "rows_affected": rows_affected,
        "execution_error": execution_error,
        "csv_export_path": csv_path,
        "reasoning_log": [reasoning_step]
    }


def _save_results_to_csv(data: list, query: str) -> str:
    """Save query results to CSV (lazy-loads pandas)."""
    if not data:
        return None

    try:
        import pandas as pd  # Lazy import - only loaded when CSV export is needed

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
