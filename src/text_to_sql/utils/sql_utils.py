"""
Simple SQL utilities for cleaning and extraction.
"""
import re
import logging

logger = logging.getLogger(__name__)


def clean_sql_query(sql_query: str) -> str:
    """Clean and normalize SQL query."""
    if not sql_query or not sql_query.strip():
        raise ValueError("Empty SQL query")
    
    # Basic cleanup
    sql_query = sql_query.strip()
    sql_query = _remove_comments(sql_query)
    sql_query = re.sub(r'\s+', ' ', sql_query)
    
    # Extract SELECT statement if buried in text
    if not sql_query.upper().startswith('SELECT'):
        match = re.search(r'(SELECT\s+.*?)(?:;|$)', sql_query, re.IGNORECASE | re.DOTALL)
        if match:
            sql_query = match.group(1)
        else:
            raise ValueError("No SELECT statement found")
    
    # Add semicolon if missing
    if not sql_query.rstrip().endswith(';'):
        sql_query = sql_query.rstrip() + ';'
    
    return sql_query


def _remove_comments(sql_query: str) -> str:
    """Remove SQL comments from query."""
    sql_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
    sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
    return sql_query


# SQL formatting removed - database handles validation, raw SQL is fine


def extract_sql_from_response(response_text: str) -> str:
    """Extract SQL query from LLM response text."""
    # Try SQL code blocks first
    match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return clean_sql_query(match.group(1))
    
    # Try to find SELECT statement
    match = re.search(r'(SELECT\s+.*?)(?:\n\n|$)', response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return clean_sql_query(match.group(1))
    
    # Fallback to whole response
    return clean_sql_query(response_text)


