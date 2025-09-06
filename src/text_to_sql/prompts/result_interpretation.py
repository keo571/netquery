"""
Result interpretation prompt templates.
"""
from typing import Dict, Any, List
import json


# Common response guidelines
_RESPONSE_GUIDELINES = """
Guidelines:
- Keep explanations technical and actionable
- Make responses conversational and helpful
- Focus on network infrastructure context (operational health, performance, capacity)
- Provide direct answers first, then supporting details
"""

ERROR_ANALYSIS_PROMPT = """Analyze the following SQL execution error and provide user-friendly guidance.

Original Query: {original_query}
Generated SQL: {sql_query}
Error: {error_message}

Provide:
1. Simple explanation of what went wrong
2. Possible causes of the error
3. Suggestions for fixing the issue
4. Alternative approaches to get the desired data
""" + _RESPONSE_GUIDELINES

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
""" + _RESPONSE_GUIDELINES


def create_result_interpretation_prompt(
    query: str,
    results: List[Dict],
    sql_query: str
) -> str:
    """Create a prompt for interpreting and explaining query results."""
    
    # Use JSON for a clean, structured data preview for the LLM
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
1. **Directly Answer the Question:** Start with a direct, concise answer to the user's original question
2. **Summarize Key Findings:** Briefly summarize the most important insights from the data
3. **Do NOT Format Tables:** Do not create markdown tables - the system handles data formatting separately
4. **Keep it Concise:** Focus on the most important information (2-3 paragraphs maximum)

{_RESPONSE_GUIDELINES.strip()}"""


def format_pipeline_response(
    original_query: str,
    results: List[Dict],
    sql_query: str,
    metadata: Dict[str, Any],
    llm_summary: str,
    include_technical_details: bool = True
) -> str:
    """Format a complete pipeline response using the template."""
    
    # Format results section
    if results:
        formatted_results = f"Found {len(results)} matching records."
    else:
        formatted_results = "No results found for your query."
    
    response_parts = [
        llm_summary,
        "",
        f"**Results:** {formatted_results}",
    ]
    
    if include_technical_details:
        response_parts.extend([
            "",
            f"**SQL Query:**",
            f"```sql",
            sql_query,
            f"```",
            "",
            f"**Execution Time:** {metadata.get('execution_time_ms', 0):.2f}ms",
            f"**Tables Used:** {', '.join(metadata.get('tables_used', []))}",
        ])
    
    return "\n".join(response_parts)