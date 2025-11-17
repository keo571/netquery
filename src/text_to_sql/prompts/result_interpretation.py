"""
Result interpretation prompt templates.
"""
from typing import Dict, Any, List
from ._shared import create_interpretation_prompt


def create_result_interpretation_prompt(
    query: str,
    results: List[Dict],
    sql_query: str = None
) -> str:
    """
    Create a prompt for interpreting and explaining query results.

    Args:
        query: User's natural language query
        results: Query results as list of dictionaries
        sql_query: Optional SQL query that was executed

    Returns:
        Formatted prompt for LLM interpretation
    """
    return create_interpretation_prompt(query, results, sql_query)