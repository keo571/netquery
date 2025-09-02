"""
SQL generation prompt templates.
"""

SQL_GENERATION_PROMPT = """You are an expert SQL query generator. Convert the natural language query to SQL using the provided database schema.

Database Schema:
{schema_context}

{plan_context}

Natural Language Query: {query}

Instructions:
1. Generate a syntactically correct SQL query
2. Use only the tables and columns shown in the schema
3. Apply appropriate WHERE clauses, JOINs, and aggregations
4. Include LIMIT clause to prevent large result sets (max {max_rows} rows)
5. Use explicit JOIN syntax instead of implicit joins
6. Ensure the query is safe (SELECT only, no data modification)
7. Handle case-insensitive string matching with UPPER() or LOWER() when appropriate
8. Optimize for performance by:
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

SQL Query:"""

SQL_GENERATION_WITH_EXAMPLES_PROMPT = """You are an expert SQL query generator. Convert the natural language query to SQL using the provided database schema and examples.

Database Schema:
{schema_context}

{plan_context}

Example Queries:
{examples}

Natural Language Query: {query}

Instructions:
1. Study the examples to understand the query patterns for this database
2. Generate a syntactically correct SQL query following similar patterns
3. Use only the tables and columns shown in the schema
4. Apply appropriate WHERE clauses, JOINs, and aggregations
5. Include LIMIT clause to prevent large result sets (max {max_rows} rows)
6. Use explicit JOIN syntax instead of implicit joins
7. Ensure the query is safe (SELECT only, no data modification)

Response Format:
```sql
-- Your SQL query here
SELECT ...
```

Explanation:
Provide a brief explanation of what the query does and why you chose this approach.

SQL Query:"""