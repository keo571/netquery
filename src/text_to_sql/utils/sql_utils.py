"""
Simple SQL utilities for cleaning and extraction.
"""
import re
import logging

SQLITE_DATE_INTERVAL_PATTERN = re.compile(
    r"(?P<func>DATE|DATETIME)\s*\(\s*'now'\s*,\s*'(?P<sign>[+-]?)(?P<amount>\d+)\s+(?P<unit>day|days|week|weeks|month|months|hour|hours|minute|minutes)'\s*\)",
    re.IGNORECASE,
)


def adapt_sql_for_database(sql_query: str, database_url: str) -> str:
    """Adapt database-specific SQL quirks (e.g., SQLite -> PostgreSQL)."""
    if not database_url:
        return sql_query

    lowered = database_url.lower()
    if lowered.startswith("postgresql") or "postgresql" in lowered:
        sql_query = _convert_sqlite_date_functions(sql_query)

    return sql_query

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


def _convert_sqlite_date_functions(sql_query: str) -> str:
    """Convert SQLite-style DATE/DATETIME usage to PostgreSQL equivalents."""

    def _replace_interval(match: re.Match) -> str:
        func = match.group('func').upper()
        sign = match.group('sign') or '+'
        amount = match.group('amount')
        unit = match.group('unit').lower()
        base = 'CURRENT_DATE' if func == 'DATE' else 'CURRENT_TIMESTAMP'
        operator = '-' if sign == '-' else '+'
        return f"{base} {operator} INTERVAL '{amount} {unit}'"

    sql_query = SQLITE_DATE_INTERVAL_PATTERN.sub(_replace_interval, sql_query)

    # Handle DATE('now') / DATETIME('now') without intervals
    sql_query = re.sub(r"DATE\s*\(\s*'now'\s*\)", "CURRENT_DATE", sql_query, flags=re.IGNORECASE)
    sql_query = re.sub(r"DATETIME\s*\(\s*'now'\s*\)", "CURRENT_TIMESTAMP", sql_query, flags=re.IGNORECASE)

    return sql_query

