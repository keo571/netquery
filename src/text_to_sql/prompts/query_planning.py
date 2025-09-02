"""
Query planning prompt templates.
"""

QUERY_PLANNING_PROMPT = """Create a query execution plan for the given natural language query.

Query: {query}

Available Tables and Schema:
{schema_context}

Instructions:
1. Identify the query intent (what the user wants to know)
2. Determine required tables and columns
3. Identify necessary filters and conditions
4. Plan any aggregations or groupings needed
5. Estimate query complexity
6. Suggest optimization strategies

Return a detailed plan in JSON format:
{{
  "intent": "Brief description of what the query should return",
  "query_type": "select|aggregate|join|complex",
  "target_tables": ["table1", "table2"],
  "required_columns": ["table.column1", "table.column2"],
  "join_conditions": [
    {{
      "left_table": "...",
      "right_table": "...",
      "condition": "left.id = right.foreign_id"
    }}
  ],
  "filters": [
    {{
      "column": "...",
      "operator": "=|>|<|LIKE|IN|BETWEEN",
      "value": "..."
    }}
  ],
  "aggregations": [
    {{
      "function": "COUNT|SUM|AVG|MIN|MAX",
      "column": "...",
      "alias": "..."
    }}
  ],
  "group_by": ["column1", "column2"],
  "order_by": [
    {{
      "column": "...",
      "direction": "ASC|DESC"
    }}
  ],
  "estimated_complexity": "simple|moderate|complex|very_complex",
  "optimization_hints": [
    "Use index on column X",
    "Consider partitioning by Y"
  ]
}}"""

QUERY_COMPLEXITY_ANALYSIS_PROMPT = """Analyze the complexity of this SQL query execution plan.

Query Plan:
{query_plan}

Factors to Consider:
1. Number of tables involved
2. Type and number of JOINs
3. Presence of subqueries
4. Aggregation functions used
5. Filtering conditions and their selectivity
6. Sorting and grouping requirements
7. Estimated data volume

Provide a complexity assessment:
{{
  "complexity_score": 1-10,
  "complexity_level": "simple|moderate|complex|very_complex",
  "bottlenecks": ["List of potential performance bottlenecks"],
  "estimated_execution_time": "fast|moderate|slow",
  "optimization_priority": ["Most important optimizations to apply"]
}}"""