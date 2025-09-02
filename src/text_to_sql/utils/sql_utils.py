"""
SQL utility functions for cleaning, formatting, and optimizing queries.
"""
import re
import sqlparse
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def clean_sql_query(sql_query: str) -> str:
    """
    Clean and validate SQL query.
    
    Args:
        sql_query: Raw SQL query string
        
    Returns:
        Cleaned SQL query
        
    Raises:
        ValueError: If query is invalid or empty
    """
    if not sql_query:
        raise ValueError("Empty SQL query")
    
    # Remove leading/trailing whitespace
    sql_query = sql_query.strip()
    
    # Remove SQL comments
    sql_query = remove_sql_comments(sql_query)
    
    # Normalize whitespace
    sql_query = re.sub(r'\s+', ' ', sql_query)
    
    # Ensure query starts with SELECT
    if not sql_query.upper().startswith('SELECT'):
        # Look for SELECT within the text
        select_match = re.search(r'(SELECT\s+.*)', sql_query, re.IGNORECASE | re.DOTALL)
        if select_match:
            sql_query = select_match.group(1)
        else:
            raise ValueError("No SELECT statement found in query")
    
    # Ensure query ends with semicolon
    if not sql_query.endswith(';'):
        sql_query += ';'
    
    # Validate basic structure
    if 'FROM' not in sql_query.upper():
        raise ValueError("Invalid SQL: missing FROM clause")
    
    # Check for balanced parentheses
    if sql_query.count('(') != sql_query.count(')'):
        raise ValueError("Invalid SQL: unbalanced parentheses")
    
    return sql_query


def remove_sql_comments(sql_query: str) -> str:
    """Remove SQL comments from query."""
    # Remove single-line comments
    sql_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
    # Remove multi-line comments
    sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
    return sql_query


def format_sql_query(sql_query: str, reindent: bool = True, keyword_case: str = 'upper') -> str:
    """
    Format SQL query for better readability.
    
    Args:
        sql_query: SQL query to format
        reindent: Whether to reindent the query
        keyword_case: Case for keywords ('upper', 'lower', 'capitalize')
        
    Returns:
        Formatted SQL query
    """
    try:
        formatted = sqlparse.format(
            sql_query,
            reindent=reindent,
            keyword_case=keyword_case,
            strip_comments=True,
            use_space_around_operators=True,
            indent_width=2
        )
        return formatted
    except Exception as e:
        logger.warning(f"Failed to format SQL: {e}")
        return sql_query


def extract_sql_from_response(response_text: str) -> str:
    """
    Extract SQL query from LLM response text.
    
    Args:
        response_text: LLM response containing SQL
        
    Returns:
        Extracted and cleaned SQL query
    """
    # Look for SQL code blocks first
    sql_block_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
    if sql_block_match:
        sql_query = sql_block_match.group(1).strip()
    else:
        # Look for any SELECT statement
        select_match = re.search(r'(SELECT\s+.*?)(?:\n\n|Explanation|$)', response_text, re.DOTALL | re.IGNORECASE)
        if select_match:
            sql_query = select_match.group(1).strip()
        else:
            # Fallback: take the whole response and try to clean it
            sql_query = response_text.strip()
    
    # Clean and return
    return clean_sql_query(sql_query)


def validate_sql_syntax(sql_query: str) -> tuple[bool, Optional[str]]:
    """
    Validate SQL syntax without executing.
    
    Args:
        sql_query: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Parse the SQL to check for syntax errors
        parsed = sqlparse.parse(sql_query)
        if not parsed:
            return False, "Failed to parse SQL query"
        
        # Additional validation checks
        sql_upper = sql_query.upper()
        
        # Must be SELECT query
        if not sql_upper.strip().startswith('SELECT'):
            return False, "Query must start with SELECT"
        
        # Must have FROM clause
        if 'FROM' not in sql_upper:
            return False, "Query must have FROM clause"
        
        # Check for dangerous operations
        dangerous_keywords = ['DELETE', 'DROP', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Dangerous operation detected: {keyword}"
        
        return True, None
        
    except Exception as e:
        return False, str(e)


def optimize_sql_query(sql_query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze and provide optimization suggestions for SQL query.
    
    Args:
        sql_query: SQL query to optimize
        config: Configuration with limits and settings
        
    Returns:
        Dictionary with optimized query and suggestions
    """
    suggestions = []
    optimized_query = sql_query
    sql_upper = sql_query.upper()
    
    # Check for SELECT *
    if 'SELECT *' in sql_upper:
        suggestions.append("Avoid SELECT * - specify only needed columns")
    
    # Check for LIMIT clause
    if 'LIMIT' not in sql_upper:
        max_rows = config.get('max_result_rows', 1000)
        optimized_query = re.sub(r';?\s*$', f' LIMIT {max_rows};', optimized_query, flags=re.IGNORECASE)
        suggestions.append(f"Added LIMIT {max_rows} to prevent large result sets")
    
    # Check for index usage hints
    if 'WHERE' in sql_upper:
        # Extract WHERE conditions
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP|ORDER|LIMIT|;|$)', sql_upper, re.IGNORECASE)
        if where_match:
            conditions = where_match.group(1)
            # Check for functions on columns (prevents index usage)
            if re.search(r'(UPPER|LOWER|SUBSTR|LENGTH)\s*\([^)]*\)', conditions):
                suggestions.append("Functions on columns may prevent index usage")
            
            # Check for wildcards at start of LIKE
            if re.search(r"LIKE\s+'%", conditions):
                suggestions.append("Leading wildcards in LIKE prevent index usage")
    
    # Check for missing JOIN conditions
    join_count = len(re.findall(r'\bJOIN\b', sql_upper))
    where_count = len(re.findall(r'\bWHERE\b|\bON\b', sql_upper))
    if join_count > 0 and where_count < join_count:
        suggestions.append("Ensure all JOINs have proper ON conditions")
    
    # Check for subqueries that could be JOINs
    if 'SELECT' in sql_upper and sql_upper.count('SELECT') > 1:
        suggestions.append("Consider replacing subqueries with JOINs for better performance")
    
    # Check for DISTINCT usage
    if 'DISTINCT' in sql_upper:
        suggestions.append("DISTINCT can be expensive - ensure it's necessary")
    
    # Check for OR conditions
    if ' OR ' in sql_upper:
        suggestions.append("OR conditions may prevent index usage - consider UNION")
    
    return {
        'original_query': sql_query,
        'optimized_query': format_sql_query(optimized_query),
        'suggestions': suggestions,
        'has_optimizations': len(suggestions) > 0
    }


def estimate_query_cost(sql_query: str) -> Dict[str, Any]:
    """
    Estimate the relative cost/complexity of a SQL query.
    
    Args:
        sql_query: SQL query to analyze
        
    Returns:
        Dictionary with cost estimation
    """
    sql_upper = sql_query.upper()
    
    # Base cost
    cost_score = 1.0
    complexity_factors = []
    
    # JOIN operations (each join adds complexity)
    join_count = len(re.findall(r'\bJOIN\b', sql_upper))
    cost_score += join_count * 0.5
    if join_count > 0:
        complexity_factors.append(f"{join_count} JOIN operations")
    
    # Subqueries (expensive)
    subquery_count = sql_upper.count('SELECT') - 1
    cost_score += subquery_count * 0.8
    if subquery_count > 0:
        complexity_factors.append(f"{subquery_count} subqueries")
    
    # Aggregations
    agg_functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP BY']
    agg_count = sum(1 for func in agg_functions if func in sql_upper)
    cost_score += agg_count * 0.3
    if agg_count > 0:
        complexity_factors.append("Aggregation functions")
    
    # DISTINCT
    if 'DISTINCT' in sql_upper:
        cost_score += 0.4
        complexity_factors.append("DISTINCT operation")
    
    # ORDER BY
    if 'ORDER BY' in sql_upper:
        cost_score += 0.2
        complexity_factors.append("Sorting")
    
    # UNION
    union_count = len(re.findall(r'\bUNION\b', sql_upper))
    cost_score += union_count * 0.6
    if union_count > 0:
        complexity_factors.append(f"{union_count} UNION operations")
    
    # Wildcards in LIKE
    if re.search(r"LIKE\s+'%", sql_upper):
        cost_score += 0.3
        complexity_factors.append("Wildcard searches")
    
    # Determine complexity level
    if cost_score < 2:
        complexity = "Simple"
    elif cost_score < 4:
        complexity = "Moderate"
    elif cost_score < 6:
        complexity = "Complex"
    else:
        complexity = "Very Complex"
    
    return {
        'cost_score': round(cost_score, 2),
        'complexity': complexity,
        'factors': complexity_factors,
        'estimated_time': 'Fast' if cost_score < 2 else 'Moderate' if cost_score < 4 else 'Slow'
    }