"""
Query execution service.

Provides the core SQL execution and caching logic used by both
/api/execute and /chat endpoints.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text

from .data_utils import format_data_for_display

logger = logging.getLogger(__name__)

# Constants (should match server.py)
MAX_CACHE_ROWS = 500
LARGE_RESULT_SET_THRESHOLD = 1000


@dataclass
class ExecutionResult:
    """Result of SQL execution."""
    data: List[Dict[str, Any]]
    columns: List[str]
    total_count: Optional[int]  # None if > LARGE_RESULT_SET_THRESHOLD
    error: Optional[str] = None


def execute_sql(
    sql: str,
    engine,
    max_rows: int = MAX_CACHE_ROWS,
    count_threshold: int = LARGE_RESULT_SET_THRESHOLD
) -> ExecutionResult:
    """
    Execute SQL query and return formatted results.

    Args:
        sql: SQL query to execute
        engine: SQLAlchemy engine
        max_rows: Maximum rows to fetch and cache
        count_threshold: Threshold for counting total rows

    Returns:
        ExecutionResult with data, columns, total_count, and any error
    """
    try:
        # Remove trailing semicolon (causes issues in subqueries)
        sql = sql.rstrip(';')

        # Step 1: Check if there's more data than threshold
        # This is faster than counting all rows
        check_more_sql = f"SELECT 1 FROM ({sql}) as sq LIMIT {count_threshold + 1}"
        with engine.connect() as conn:
            check_results = conn.execute(text(check_more_sql)).fetchall()
            has_more_than_threshold = len(check_results) > count_threshold

            # Set total_count based on threshold
            if has_more_than_threshold:
                total_count = None  # Unknown exact count (> threshold)
            else:
                total_count = len(check_results)  # Exact count ≤ threshold

        # Step 2: Fetch actual data (up to max_rows)
        if 'LIMIT' in sql.upper():
            # Use existing LIMIT clause
            limited_sql = sql
        else:
            limited_sql = f"{sql} LIMIT {max_rows}"

        with engine.connect() as conn:
            result = conn.execute(text(limited_sql))
            rows = result.fetchall()
            columns = list(result.keys())

        # Convert to list of dicts
        data = [dict(zip(columns, row)) for row in rows]

        # Format data for display (timestamps, decimal precision)
        data = format_data_for_display(data)

        return ExecutionResult(
            data=data,
            columns=columns,
            total_count=total_count,
            error=None
        )

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return ExecutionResult(
            data=[],
            columns=[],
            total_count=None,
            error=str(e)
        )
