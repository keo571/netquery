"""
Result interpretation prompt templates.
"""
from typing import Dict, Any, List
from ._shared import create_interpretation_prompt

# Main interpretation prompt - uses shared utilities
def create_result_interpretation_prompt(
    query: str,
    results: List[Dict],
    sql_query: str = None
) -> str:
    """Create a prompt for interpreting and explaining query results."""
    return create_interpretation_prompt(query, results, sql_query)

# Legacy templates for backward compatibility
ERROR_ANALYSIS_PROMPT = """Analyze this SQL execution error and provide user-friendly guidance.

Original Query: {original_query}
Generated SQL: {sql_query}
Error: {error_message}

Provide:
1. Simple explanation of what went wrong
2. Possible causes and suggestions for fixing
3. Alternative approaches

Keep explanations technical but actionable for network engineers."""

def format_pipeline_response(
    original_query: str = None,
    results: List[Dict] = None,
    sql_query: str = None,
    metadata: Dict[str, Any] = None,
    llm_summary: str = "",
    include_technical_details: bool = True
) -> str:
    """Format a complete pipeline response."""
    count = len(results) if results else 0

    response_parts = [llm_summary]

    if results:
        response_parts.append(f"\n**Results:** Found {count} matching records.")
    else:
        response_parts.append(f"\n**Results:** No results found.")

    if include_technical_details and sql_query:
        response_parts.extend([
            f"\n**SQL Query:**\n```sql\n{sql_query}\n```",
            f"\n**Execution Time:** {metadata.get('execution_time_ms', 0):.1f}ms"
        ])

    return "".join(response_parts)