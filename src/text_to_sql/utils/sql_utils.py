"""
Simple SQL utilities for cleaning and basic validation.
"""
import re
import sqlparse
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


def format_sql_query(sql_query: str) -> str:
    """Format SQL query for readability."""
    try:
        # Format with compact style
        formatted = sqlparse.format(
            sql_query,
            reindent=False,  # Don't split columns onto separate lines
            keyword_case='upper',
            identifier_case='lower',
            strip_comments=True,
            use_space_around_operators=True
        )
        
        # Clean up whitespace and format nicely
        formatted = re.sub(r'\s+', ' ', formatted)  # Normalize whitespace
        formatted = formatted.replace('SELECT ', 'SELECT ')
        formatted = formatted.replace(' FROM ', '\nFROM ')
        formatted = formatted.replace(' WHERE ', '\nWHERE ')
        formatted = formatted.replace(' GROUP BY ', '\nGROUP BY ')
        formatted = formatted.replace(' ORDER BY ', '\nORDER BY ')
        formatted = formatted.replace(' LIMIT ', '\nLIMIT ')
        formatted = formatted.replace(' JOIN ', '\n  JOIN ')
        formatted = formatted.replace(' LEFT JOIN ', '\n  LEFT JOIN ')
        formatted = formatted.replace(' RIGHT JOIN ', '\n  RIGHT JOIN ')
        formatted = formatted.replace(' INNER JOIN ', '\n  INNER JOIN ')
        formatted = formatted.replace(' AND ', '\n  AND ')
        formatted = formatted.replace(' OR ', '\n   OR ')
        
        return formatted.strip()
    except Exception:
        return sql_query


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


