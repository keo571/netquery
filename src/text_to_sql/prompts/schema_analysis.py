"""
Schema analysis prompt templates.
"""

SCHEMA_ANALYSIS_PROMPT = """Analyze the database schema to identify the most relevant tables for answering the given query.

Query: {query}

Available Tables:
{tables_list}

Instructions:
1. Identify which tables are most likely to contain the data needed
2. Consider table relationships and foreign keys
3. Look for tables with relevant column names
4. Rank tables by relevance (0.0 to 1.0)
5. Include any junction tables needed for many-to-many relationships

Return a JSON object with:
{{
  "relevant_tables": [
    {{
      "table_name": "...",
      "relevance_score": 0.95,
      "reason": "Contains the primary data for..."
    }}
  ],
  "relationships": [
    {{
      "from_table": "...",
      "to_table": "...",
      "via_column": "...",
      "relationship_type": "one-to-many"
    }}
  ]
}}"""

TABLE_RELEVANCE_PROMPT = """Given a natural language query and a database table, determine how relevant this table is for answering the query.

Query: {query}

Table Name: {table_name}
Table Description: {table_description}
Column Names: {column_names}
Sample Data: {sample_data}

Rate the relevance on a scale of 0.0 to 1.0 where:
- 1.0 = Essential for answering the query
- 0.7-0.9 = Very relevant, likely needed
- 0.4-0.6 = Potentially relevant, might be needed for joins
- 0.1-0.3 = Slightly relevant, unlikely to be needed
- 0.0 = Not relevant at all

Response Format:
{{
  "relevance_score": 0.X,
  "reasoning": "This table is relevant because...",
  "key_columns": ["column1", "column2"]
}}"""