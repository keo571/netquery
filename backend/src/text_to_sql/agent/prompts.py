"""
Prompts for the Text-to-SQL agent.
Centralized prompt management for consistent LLM interactions.
"""
from datetime import datetime
from typing import Dict, Any, List
import json


def get_current_date() -> str:
    """Get current date in a readable format."""
    return datetime.now().strftime("%B %d, %Y")


# SQL Generation System Prompt
SQL_GENERATION_SYSTEM_PROMPT = """You are an expert SQL query generator specializing in converting natural language questions into syntactically correct and efficient SQL queries.

## Core Responsibilities:
1. Generate safe, SELECT-only SQL queries
2. Use proper JOIN syntax and optimization techniques
3. Apply appropriate filters and conditions
4. Include LIMIT clauses to prevent large result sets
5. Handle case-insensitive string matching when appropriate

## Safety Guidelines:
- ONLY generate SELECT statements
- NO data modification operations (INSERT, UPDATE, DELETE, DROP, etc.)
- Always include LIMIT clause (max 1000 rows)
- Use parameterized patterns when possible
- Avoid dynamic SQL construction

## Best Practices:
- Use explicit JOIN syntax instead of WHERE-based joins
- Specify column names instead of SELECT *
- Apply appropriate WHERE conditions
- Use UPPER() or LOWER() for case-insensitive string comparisons
- Order results logically when appropriate

Current date: {current_date}"""


# Query Classification Prompt
QUERY_CLASSIFICATION_PROMPT = """Analyze the following natural language query and classify its intent and complexity.

Query: {query}

Available Schema:
{schema_context}

Classify the query based on:

1. **Primary Intent:**
   - simple_select: Basic data retrieval from one table
   - filtered_select: Data retrieval with WHERE conditions
   - aggregation: COUNT, SUM, AVG, MIN, MAX operations
   - join_query: Multi-table operations
   - complex_analysis: Complex queries with subqueries, multiple joins

2. **Complexity Level:**
   - simple: Single table, basic conditions
   - medium: Multiple tables or aggregations
   - complex: Advanced operations, subqueries, complex logic

3. **Required Tables:** List of tables needed for the query

Respond in JSON format:
{{
    "intent": "primary_intent",
    "complexity": "simple|medium|complex", 
    "confidence": 0.95,
    "required_tables": ["table1", "table2"],
    "reasoning": "Brief explanation of classification"
}}"""


# SQL Explanation Prompt
SQL_EXPLANATION_PROMPT = """Explain the following SQL query in simple terms that a non-technical user would understand.

SQL Query:
{sql_query}

Natural Language Query:
{original_query}

Explain:
1. What data the query retrieves
2. From which tables
3. What conditions/filters are applied
4. How the results are organized

Keep the explanation concise and user-friendly."""


# Query Optimization Prompt
QUERY_OPTIMIZATION_PROMPT = """Analyze and optimize the following SQL query for better performance and readability.

Original Query:
{sql_query}

Schema Context:
{schema_context}

Provide:
1. Optimized version of the query
2. List of specific improvements made
3. Performance impact explanation
4. Any additional recommendations

Focus on:
- Index utilization
- JOIN optimization
- Query structure improvements
- Best practice compliance"""


# Error Analysis Prompt
ERROR_ANALYSIS_PROMPT = """Analyze the following SQL execution error and provide user-friendly guidance.

Original Query: {original_query}
Generated SQL: {sql_query}
Error: {error_message}

Provide:
1. Simple explanation of what went wrong
2. Possible causes of the error
3. Suggestions for fixing the issue
4. Alternative approaches to get the desired data

Keep explanations non-technical and actionable."""


# Response Formatting Template
RESPONSE_FORMAT_TEMPLATE = """Format a comprehensive response for the user's query.

Original Query: {original_query}
Results: {results}
Execution Time: {execution_time}ms
Row Count: {row_count}

Include:
1. Direct answer to the user's question
2. Well-formatted data presentation
3. Key insights from the results
4. Brief explanation of how the answer was found

Make the response conversational and helpful."""


def create_sql_generation_prompt(
    query: str,
    schema_context: str,
    query_plan: Dict[str, Any] = None,
    tables: List[str] = None
) -> str:
    """Create a comprehensive SQL generation prompt."""
    
    current_date = get_current_date()
    
    # Build context sections
    plan_section = ""
    if query_plan:
        plan_section = f"""
## Query Analysis:
- Intent: {query_plan.get('intent', 'unknown')}
- Complexity: {query_plan.get('estimated_complexity', 'medium')}
- Target Tables: {', '.join(query_plan.get('target_tables', []))}
- Requires Joins: {'Yes' if len(tables or []) > 1 else 'No'}
"""
    
    safety_reminders = """
## Safety Requirements:
- Generate SELECT statements ONLY
- Include LIMIT clause (max 1000 rows)
- Use explicit JOIN syntax
- Handle string comparisons with UPPER()/LOWER() for case-insensitivity
"""
    
    return f"""{SQL_GENERATION_SYSTEM_PROMPT.format(current_date=current_date)}

{plan_section}

## Database Schema:
{schema_context}

{safety_reminders}

## Task:
Convert this natural language query to SQL:
"{query}"

## Response Format:
```sql
-- Your optimized SQL query here
SELECT ...
```

## Explanation:
Provide a brief explanation of the query approach and any assumptions made."""


def create_query_validation_prompt(sql_query: str, original_query: str) -> str:
    """Create a prompt for query validation and improvement suggestions."""
    
    return f"""Review the following SQL query for correctness, safety, and optimization opportunities.

Original Request: {original_query}
Generated SQL: {sql_query}

Evaluate:
1. **Correctness**: Does the SQL accurately address the original request?
2. **Safety**: Are there any security concerns or dangerous operations?
3. **Performance**: Can the query be optimized for better performance?
4. **Best Practices**: Does it follow SQL best practices?

Provide specific, actionable feedback and suggestions for improvement."""


def create_result_interpretation_prompt(
    query: str,
    results: List[Dict],
    sql_query: str
) -> str:
    """Create a prompt for interpreting and explaining query results."""
    
    # NEW: Use JSON for a clean, structured data preview for the LLM
    try:
        results_preview = json.dumps(results[:3], indent=2) if results else "No results returned."
    except TypeError:
        # Fallback for non-serializable data types
        results_preview = str(results[:3]) if results else "No results returned."

    return f"""Your task is to interpret database query results for a network engineer.

**Original Question:** "{query}"
**SQL Query Used:** 
```sql
{sql_query}
```

**Query Results (JSON Sample):**
```json
{results_preview}
```

**Instructions:**
1.  **Directly Answer the Question:** Start by providing a direct, concise answer to the user's original question.
2.  **Summarize Key Findings:** Briefly summarize the most important insights from the data. For example, "There is one degraded load balancer" or "All certificates are valid."
3.  **Do NOT Format a Table:** Do not attempt to create a markdown table or any other visual table format. The system will handle data formatting separately.
4.  **Be Conversational:** Keep the tone helpful and informative, as if you are an expert assistant.

Provide your interpretation below:"""


# Template for comprehensive agent responses
AGENT_RESPONSE_TEMPLATE = """## Query Analysis
**Your Question:** {original_query}
**Complexity:** {complexity}
**Tables Used:** {tables_used}

## Summary
{llm_summary}

## Data
{formatted_results}

## Query Details
**SQL Generated:**
```sql
{sql_query}
```

**Execution Time:** {execution_time}ms
**Confidence Score:** {confidence_score:.2f}

{additional_insights}"""


def format_agent_response(
    original_query: str,
    results: List[Dict],
    sql_query: str,
    metadata: Dict[str, Any],
    llm_summary: str, # NEW: Pass in the LLM's summary
    include_technical_details: bool = True
) -> str:
    """Format a complete agent response using the template."""
    
    # Format results section
    if results:
        # The main system now handles HTML table generation,
        # so we can provide a simple count here or a text table as a fallback.
        formatted_results = f"Found {len(results)} matching records."
    else:
        formatted_results = "No results found for your query."
    
    # Generate insights
    insights = _generate_result_insights(results, original_query)
    
    if include_technical_details:
        return AGENT_RESPONSE_TEMPLATE.format(
            original_query=original_query,
            complexity=metadata.get('complexity', 'medium'),
            tables_used=', '.join(metadata.get('tables_used', [])),
            llm_summary=llm_summary, # Use the LLM summary
            formatted_results=formatted_results,
            sql_query=sql_query,
            execution_time=metadata.get('execution_time_ms', 0),
            confidence_score=metadata.get('confidence_score', 0.0),
            additional_insights=insights
        )
    else:
        # Simplified response without technical details
        return f"""## Answer to: {original_query}

{llm_summary}

{formatted_results}

{insights}"""


def _generate_result_insights(results: List[Dict], query: str) -> str:
    """Generate insights from query results."""
    if not results:
        return "## Insights\nNo data found matching your criteria."
    
    insights = []
    
    # Basic statistics
    row_count = len(results)
    if row_count == 1:
        insights.append("Found exactly one matching record")
    else:
        insights.append(f"Found {row_count} matching records")
    
    # Column analysis
    if results:
        numeric_cols = [k for k, v in results[0].items() if isinstance(v, (int, float))]
        if numeric_cols:
            insights.append(f"Numeric data available for analysis: {', '.join(numeric_cols[:3])}")
    
    insight_text = "\n".join(f"- {insight}" for insight in insights[:3])
    return f"## Insights\n{insight_text}" if insight_text else ""