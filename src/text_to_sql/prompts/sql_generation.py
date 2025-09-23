"""
SQL generation prompt templates.
"""
from ._shared import create_sql_prompt

# Main SQL generation prompt - uses shared utilities
def SQL_GENERATION_PROMPT_FUNC(query: str, schema_context: str, query_plan: str, database_url: str = "") -> str:
    """Generate SQL generation prompt with query plan context."""
    return create_sql_prompt(query, schema_context, str(query_plan), database_url)

# Legacy string template for backward compatibility
SQL_GENERATION_PROMPT = """Generate SQL for this query using the schema and plan provided.

Schema: {schema_context}

Plan: {query_plan}

Query: "{query}"

1. Generate syntactically correct SQLite queries (SELECT only)
2. Use only tables and columns from the provided schema
3. Use explicit JOIN syntax, not implicit joins
4. Handle dates with DATE() function: DATE('now', '+30 days'), DATE('now', '-1 week')
5. For case-insensitive matching use UPPER() or LOWER()
6. Optimize: select specific columns, use indexes, prefer JOINs over subqueries

For window functions or ranking, use subqueries (NOT CTEs):
- NEVER use WITH clauses or CTEs - they cause syntax errors
- Use subqueries instead: SELECT * FROM (SELECT *, ROW_NUMBER() OVER (...) FROM table) WHERE rn <= N
- For complex queries, break into simpler SELECT statements with JOINs

Network Infrastructure Focus:
- Load balancers, servers, VIPs, SSL certificates, monitoring data
- Key attributes: status, datacenter, health_score, utilization
- Common thresholds: high (>80%), low (<30%), many (>100)
- Time context: recent = last 7 days, soon = next 30 days

Response Format:
```sql
SELECT ...
```
Brief explanation of the query approach."""