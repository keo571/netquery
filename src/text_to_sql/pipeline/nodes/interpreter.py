"""
Interpreter node for Text-to-SQL pipeline.
"""
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

from ...config import config
from ..state import TextToSQLState
from ...prompts import create_result_interpretation_prompt

logger = logging.getLogger(__name__)


def interpreter_node(state: TextToSQLState) -> Dict[str, Any]:
    """Format final response with query results."""
    # Check for pre-set response from error handling
    if state.get("final_response"):
        return {"formatted_response": state["final_response"]}

    # Handle execution errors
    if state.get("execution_error"):
        return {"formatted_response": f"An error occurred: {state['execution_error']}"}
    
    if state["include_reasoning"]:
        return {"formatted_response": _create_full_response(state)}
    else:
        # Simple data table only
        data_table = _format_table_as_markdown(state["query_results"])
        return {"formatted_response": data_table}


def _format_table_as_markdown(data: List[Dict[str, Any]]) -> str:
    """Convert a list of dictionaries to a Markdown table."""
    if not data:
        return "No data available"
    
    headers = list(data[0].keys())
    
    # Header row
    table = "| " + " | ".join(headers) + " |\n"
    # Separator row  
    table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    # Data rows
    for row in data:
        values = [str(row.get(h, "") or "") for h in headers]
        table += "| " + " | ".join(values) + " |\n"
    
    return table


def _create_full_response(state: TextToSQLState) -> str:
    """Create full response with LLM insights and reasoning."""
    llm = ChatGoogleGenerativeAI(
        model=config.llm.model_name,
        temperature=config.llm.temperature,
        max_retries=config.llm.max_retries,
        api_key=config.llm.effective_api_key
    )
    
    # Generate insights
    prompt = create_result_interpretation_prompt(
        query=state["original_query"],
        results=state["query_results"],
        sql_query=state["generated_sql"]
    )
    insights = llm.invoke(prompt).content
    
    # Generate SQL explanation
    sql_explanation = _generate_sql_explanation(
        llm, state["original_query"], state["generated_sql"]
    )
    
    # Build reasoning section
    reasoning_text = "## Process\n"
    for step in state.get("reasoning_log", []):
        step_name = step.get('step_name', 'Step')
        step_details = step.get('details', 'Completed')
        reasoning_text += f"- **{step_name}:** {step_details}\n"
    
    # Format data table
    data_table = _format_table_as_markdown(state["query_results"])
    
    # Metadata
    execution_time = state.get("execution_time_ms", 0.0)
    row_count = len(state.get("query_results", []))
    
    return f"""## SQL Query
```sql
{state['generated_sql']}
```

## Explanation
{sql_explanation}

{reasoning_text}

{data_table}

## Analysis
{insights}

---
*Execution: {execution_time:.1f}ms | Rows: {row_count}*"""


def _generate_sql_explanation(llm, original_query: str, sql_query: str) -> str:
    """Generate an explanation of the SQL query using LLM."""
    
    explanation_prompt = f"""
You are a SQL expert helping users understand database queries.

Original Question: "{original_query}"

Generated SQL:
```sql
{sql_query}
```

Please provide a clear, concise explanation of:
1. What this SQL query does
2. Which tables it accesses and why
3. What conditions or filters are applied
4. How it answers the original question

Focus on the SQL mechanics and logic, not the specific results.
Keep it simple and educational.
"""
    
    try:
        response = llm.invoke(explanation_prompt)
        return response.content.strip()
    except Exception as e:
        logger.warning(f"Failed to generate SQL explanation: {e}")
        return "SQL explanation generation failed."






