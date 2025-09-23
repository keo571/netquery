"""
Shared prompt components and utilities.
"""

# Core database instructions for SQLite
DATABASE_INSTRUCTIONS = """
1. Generate syntactically correct SQLite queries (SELECT only)
2. Use only tables and columns from the provided schema
3. Use explicit JOIN syntax, not implicit joins
4. Handle dates with DATE() function: DATE('now', '+30 days'), DATE('now', '-1 week')
5. For case-insensitive matching use UPPER() or LOWER()
6. Column optimization: select only the minimum columns needed to answer the query
7. Prefer essential data columns over metadata/system columns unless specifically requested
"""

# Network infrastructure context
NETWORK_CONTEXT = """
Network Infrastructure Focus:
- Load balancers, servers, VIPs, SSL certificates, monitoring data
- Key attributes: status, datacenter, health_score, utilization
- Common thresholds: high (>80%), low (<30%), many (>100)
- Time context: recent = last 7 days, soon = next 30 days
"""

# Standard response format
RESPONSE_FORMAT = """
Response Format:
```sql
SELECT ...
```
Brief explanation of the query approach.
"""

# JSON format for query planning
JSON_FORMAT = """
Return ONLY valid JSON with these fields:
- intent: query type (select_with_filter, join_and_aggregate, etc.)
- target_tables: [table names]
- required_columns: ["table.column", ...]
- filters: [{"column": "table.col", "operator": "=", "value": "x"}]
- aggregations: [{"function": "SUM", "column": "table.col", "alias": "name"}]
- sorting: {"column": "table.col", "direction": "DESC"} or null
- grouping: ["table.col"] or null
- joins: [{"type": "INNER", "left_table": "a", "right_table": "b", "on": "a.id = b.id"}]
- estimated_complexity: "simple"/"medium"/"complex"
"""

def create_sql_prompt(query: str, schema_context: str, query_plan: str) -> str:
    """Create optimized SQL generation prompt."""
    return f"""Generate SQL for this query using the schema and plan provided.

Schema: {schema_context}

Plan: {query_plan}

Query: "{query}"

{DATABASE_INSTRUCTIONS}
{NETWORK_CONTEXT}
{RESPONSE_FORMAT}"""

def create_planning_prompt(query: str, schema_context: str) -> str:
    """Create optimized query planning prompt."""
    return f"""Analyze this query and create an execution plan.

Query: "{query}"
Schema: {schema_context}

Instructions:
1. Identify intent, tables, columns, filters, joins, aggregations
2. For vague terms: "high" = >80%, "low" = <30%, "recent" = last 7 days
3. Add LIMIT 50-100 for broad queries like "show all [table]"
4. Column selection strategy:
   - Analyze the query to determine what information is actually needed
   - Include only columns that directly answer the question asked
   - Add identifier columns (like name, id) only if needed for clarity
   - Avoid metadata columns (created_at, updated_at) unless specifically requested

{JSON_FORMAT}"""

def create_interpretation_prompt(query: str, results: list, sql_query: str = None) -> str:
    """Create streamlined result interpretation prompt."""
    count = len(results) if results else 0
    return f"""Analyze these query results for a network engineer.

Original Query: "{query}"
Results: {count} rows
SQL: {sql_query or "Not provided"}

Provide:
1. Direct answer to the question
2. Key insights from the data (percentages, patterns, anomalies)
3. Operational impact (what does this mean for network operations?)
4. Actionable recommendations

Focus on network infrastructure context: status distributions, datacenter patterns, capacity issues, health concerns."""