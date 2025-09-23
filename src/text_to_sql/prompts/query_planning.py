"""
Query planning prompt templates.
"""
from ._shared import create_planning_prompt

# Main query planning prompt - uses shared utilities
def QUERY_PLANNING_PROMPT_FUNC(query: str, schema_context: str) -> str:
    """Generate query planning prompt."""
    return create_planning_prompt(query, schema_context)

# Legacy string template for backward compatibility
QUERY_PLANNING_PROMPT = """Analyze this query and create an execution plan.

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

Return ONLY valid JSON with these fields:
- intent: query type (select_with_filter, join_and_aggregate, etc.)
- target_tables: [table names]
- required_columns: ["table.column", ...]
- filters: [{{"column": "table.col", "operator": "=", "value": "x"}}]
- aggregations: [{{"function": "SUM", "column": "table.col", "alias": "name"}}]
- sorting: {{"column": "table.col", "direction": "DESC"}} or null
- grouping: ["table.col"] or null
- joins: [{{"type": "INNER", "left_table": "a", "right_table": "b", "on": "a.id = b.id"}}]
- estimated_complexity: "simple"/"medium"/"complex"

Example:
{{
    "intent": "select_with_filter",
    "target_tables": ["load_balancers"],
    "required_columns": ["load_balancers.name", "load_balancers.status"],
    "filters": [{{"column": "load_balancers.status", "operator": "=", "value": "active"}}],
    "aggregations": [],
    "sorting": null,
    "grouping": null,
    "joins": [],
    "estimated_complexity": "simple"
}}"""