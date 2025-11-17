"""
Shared prompt components and utilities.
"""

def get_database_instructions(database_url: str = "") -> str:
    """Get database-specific SQL instructions."""
    if database_url.startswith('sqlite'):
        return """
1. Generate syntactically correct SQLite queries (SELECT only)
2. Use only tables and columns from the provided schema
3. Use explicit JOIN syntax, not implicit joins
4. Handle dates with DATE() function: DATE('now', '+30 days'), DATE('now', '-1 week')
5. For case-insensitive matching use UPPER() or LOWER()
6. Column optimization: select only the minimum columns needed to answer the query
7. Prefer essential data columns over metadata/system columns unless specifically requested
8. **Never include UUID columns in SELECT clause** - UUID columns can be used in JOINs and WHERE clauses, but should never appear in the SELECT list as they are not human-readable

**CRITICAL ID/Name Rule:**
- When returning an entity's ID, ALWAYS include its human-readable identifier (name, address, title, etc.)
- Example: SELECT id, name FROM load_balancers (NOT just SELECT id)
- Example: SELECT vip_id, vip_address FROM virtual_ips (NOT just SELECT vip_id)
- If ONLY returning the name/address (no id), then id is not needed
- This ensures results are meaningful and understandable to users
"""
    elif 'postgresql' in database_url.lower():
        return """
1. Generate syntactically correct PostgreSQL queries (SELECT only)
2. Use only tables and columns from the provided schema
3. Use explicit JOIN syntax, not implicit joins
4. Handle dates with CURRENT_DATE, INTERVAL: CURRENT_DATE + INTERVAL '30 days', CURRENT_DATE - INTERVAL '1 week'
5. For case-insensitive matching use ILIKE or UPPER()/LOWER()
6. Column optimization: select only the minimum columns needed to answer the query
7. Prefer essential data columns over metadata/system columns unless specifically requested
8. Use double quotes for identifiers if needed: "column_name"
9. **Never include UUID columns in SELECT clause** - UUID columns can be used in JOINs and WHERE clauses, but should never appear in the SELECT list as they are not human-readable

**CRITICAL ID/Name Rule:**
- When returning an entity's ID, ALWAYS include its human-readable identifier (name, address, title, etc.)
- Example: SELECT id, name FROM load_balancers (NOT just SELECT id)
- Example: SELECT vip_id, vip_address FROM virtual_ips (NOT just SELECT vip_id)
- If ONLY returning the name/address (no id), then id is not needed
- This ensures results are meaningful and understandable to users
"""
    else:
        # Generic SQL instructions
        return """
1. Generate syntactically correct SQL queries (SELECT only)
2. Use only tables and columns from the provided schema
3. Use explicit JOIN syntax, not implicit joins
4. Handle dates appropriately for your database system
5. For case-insensitive matching use appropriate functions for your database
6. Column optimization: select only the minimum columns needed to answer the query
7. Prefer essential data columns over metadata/system columns unless specifically requested
8. **Never include UUID columns in SELECT clause** - UUID columns can be used in JOINs and WHERE clauses, but should never appear in the SELECT list as they are not human-readable

**CRITICAL ID/Name Rule:**
- When returning an entity's ID, ALWAYS include its human-readable identifier (name, address, title, etc.)
- Example: SELECT id, name FROM load_balancers (NOT just SELECT id)
- Example: SELECT vip_id, vip_address FROM virtual_ips (NOT just SELECT vip_id)
- If ONLY returning the name/address (no id), then id is not needed
- This ensures results are meaningful and understandable to users
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

def create_sql_prompt(query: str, schema_context: str, query_plan: str, database_url: str = "") -> str:
    """Create optimized SQL generation prompt."""
    database_instructions = get_database_instructions(database_url)
    return f"""Generate SQL for this query using the schema and plan provided.

Schema: {schema_context}

Plan: {query_plan}

Query: "{query}"

{database_instructions}
{NETWORK_CONTEXT}
{RESPONSE_FORMAT}"""

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