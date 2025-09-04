"""
Query planning prompt templates.
"""

QUERY_PLANNING_PROMPT = """You are a SQL query planner. Analyze the natural language query and create a detailed execution plan.

Natural Language Query: {query}

Available Schema:
{schema_context}

Instructions:
1. Identify the main intent (select, aggregate, filter, join, etc.)
2. Determine which tables and columns are needed
3. Identify any filters, aggregations, or sorting requirements
4. For temporal queries (like "next 30 days", "last week"), convert to database-compatible date filters
5. Determine if joins are needed and what type
6. Assess the complexity level

CRITICAL: Respond with ONLY a valid JSON object. No explanations, no additional text before or after. Just the JSON object.

JSON format:
- intent: main query intent
- target_tables: list of tables needed
- required_columns: list of columns in "table.column" format
- filters: list of filter conditions with table-qualified columns
- aggregations: list of aggregation operations
- sorting: sorting requirements with table-qualified columns
- grouping: grouping requirements with table-qualified columns
- joins: list of join operations needed
- estimated_complexity: "simple", "medium", or "complex"

Examples:

Single table query:
{{
    "intent": "select_with_filter",
    "target_tables": ["employees"],
    "required_columns": ["employees.first_name", "employees.last_name", "employees.salary"],
    "filters": [
        {{"column": "employees.department", "operator": "=", "value": "Engineering"}}
    ],
    "aggregations": [],
    "sorting": {{"column": "employees.salary", "direction": "DESC"}},
    "grouping": null,
    "joins": [],
    "estimated_complexity": "simple"
}}

Multi-table query with join:
{{
    "intent": "join_and_aggregate",
    "target_tables": ["orders", "customers"],
    "required_columns": ["customers.name", "orders.total_amount", "orders.order_date"],
    "filters": [
        {{"column": "orders.order_date", "operator": ">", "value": "2024-01-01"}}
    ],
    "aggregations": [
        {{"function": "SUM", "column": "orders.total_amount", "alias": "total_revenue"}}
    ],
    "sorting": {{"column": "total_revenue", "direction": "DESC"}},
    "grouping": ["customers.name"],
    "joins": [
        {{"type": "INNER", "left_table": "orders", "right_table": "customers", 
          "on": "orders.customer_id = customers.id"}}
    ],
    "estimated_complexity": "medium"
}}

Temporal query example:
{{
    "intent": "select_with_temporal_filter",
    "target_tables": ["ssl_certificates"],
    "required_columns": ["ssl_certificates.domain", "ssl_certificates.expiry_date", "ssl_certificates.status"],
    "filters": [
        {{"column": "ssl_certificates.expiry_date", "operator": "BETWEEN", "value": "CURRENT_DATE AND DATE(CURRENT_DATE, '+30 days')"}}
    ],
    "aggregations": [],
    "sorting": {{"column": "ssl_certificates.expiry_date", "direction": "ASC"}},
    "grouping": null,
    "joins": [],
    "estimated_complexity": "simple"
}}

IMPORTANT: Always return valid JSON. Never include explanatory text outside the JSON object.

Query to plan: {query}
"""