"""
SQL generation prompt templates.
"""

# Common instructions shared across SQL generation prompts
_COMMON_SQL_INSTRUCTIONS = """
Instructions:
1. Generate a syntactically correct SQL query for SQLite database
2. Use only the tables and columns shown in the schema
3. Apply appropriate WHERE clauses, JOINs, and aggregations
4. Include LIMIT clause to prevent large result sets (max {max_rows} rows)
5. Use explicit JOIN syntax instead of implicit joins
6. Ensure the query is safe (SELECT only, no data modification)
7. Handle case-insensitive string matching with UPPER() or LOWER() when appropriate
8. For date operations in SQLite, use:
   - DATE() function for date calculations
   - Example: DATE('now', '+30 days') for 30 days from now
   - Example: DATE('now', '-1 week') for one week ago
   - Use DATE() instead of INTERVAL syntax
9. Optimize for performance by:
   - Selecting only necessary columns (avoid SELECT *)
   - Using appropriate indexes where possible
   - Minimizing subqueries when JOINs would be more efficient

Response Format:
```sql
-- Your SQL query here
SELECT ...
```

Explanation:
Provide a brief explanation of what the query does and why you chose this approach.
"""

SQL_GENERATION_PROMPT = """You are an expert SQL query generator. Convert the natural language query to SQL using the provided database schema and query plan.

Database Schema:
{schema_context}

Query Plan:
{query_plan}

Natural Language Query: {query}
""" + _COMMON_SQL_INSTRUCTIONS

SQL_GENERATION_WITH_EXAMPLES_PROMPT = """You are an expert SQL query generator. Convert the natural language query to SQL using the provided database schema and examples.

Database Schema:
{schema_context}

{plan_context}

Example Queries:
{examples}

Natural Language Query: {query}

Additional Instruction:
- Study the examples to understand the query patterns for this database
- Generate a query following similar patterns from the examples
""" + _COMMON_SQL_INSTRUCTIONS