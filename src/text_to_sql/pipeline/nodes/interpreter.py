"""
Interpreter node for Text-to-SQL pipeline.
Interprets query results and formats the final response using LLM.
"""
from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import logging
import os

from ...config import config as text_to_sql_config
from ..state import TextToSQLState, ReasoningStep
from ..prompts import (
    create_result_interpretation_prompt,
    format_pipeline_response,
    RESPONSE_FORMAT_TEMPLATE,
    ERROR_ANALYSIS_PROMPT
)

logger = logging.getLogger(__name__)


def _format_table_as_html(data: List[Dict[str, Any]], css_class: str = "styled-table") -> str:
    """
    Convert a list of dictionaries to an HTML table.
    Replaces pandas DataFrame.to_html() functionality.
    """
    if not data:
        return "<p>No data available</p>"
    
    # Get column headers from first row
    headers = list(data[0].keys()) if data else []
    
    # Build HTML table
    html_parts = [f'<table class="{css_class}" border="0">']
    
    # Add header row
    html_parts.append("<thead><tr>")
    for header in headers:
        html_parts.append(f"<th>{header}</th>")
    html_parts.append("</tr></thead>")
    
    # Add data rows
    html_parts.append("<tbody>")
    for row in data:
        html_parts.append("<tr>")
        for header in headers:
            value = row.get(header, "")
            # Handle None values
            if value is None:
                value = ""
            html_parts.append(f"<td>{value}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody>")
    
    html_parts.append("</table>")
    return "".join(html_parts)


def _simple_markdown_to_html(text: str) -> str:
    """
    Simple markdown to HTML conversion.
    Replaces the markdown library for basic formatting.
    """
    # Handle code blocks
    import re
    
    # Convert code blocks
    text = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Convert headers
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Convert bold and italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    
    # Convert line breaks
    text = re.sub(r'\n\n', r'</p><p>', text)
    
    # Wrap in paragraph tags if not already wrapped
    if not text.startswith('<'):
        text = f'<p>{text}</p>'
    
    return text


def _format_reasoning_log(log: List[ReasoningStep]) -> str:
    if not log:
        return ""
    
    lines = ["\n**Reasoning Process:**"]
    for i, step in enumerate(log, 1):
        name = step.get('step_name', 'Unknown Step')
        status = step.get('status', '✅')
        details = step.get('details', 'No details provided.')
        lines.append(f"{i}. {status} **{name}**: {details}")
        
    return "\n".join(lines)


def interpret_results_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Interprets the query results and formats the final response.
    Toggles between a full analysis and a data-only view.
    """
    run_config = state.get("run_config", {})
    include_reasoning = run_config.get("include_reasoning", False)
    
    # DEBUG: Add detailed logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 INTERPRETER DEBUG:")
    logger.info(f"🔍 Raw run_config: {run_config}")
    logger.info(f"🔍 Include reasoning: {include_reasoning}")
    logger.info(f"🔍 Type of include_reasoning: {type(include_reasoning)}")
    logger.info(f"🔍 run_config keys: {list(run_config.keys()) if run_config else 'No run_config'}")
    
    final_response_str = ""

    if state.get("execution_error"):
        final_response_str = f"An error occurred: {state['execution_error']}"
        logger.info("🔍 Taking ERROR path")

    elif include_reasoning:
        logger.info("🔍 Taking REASONING path - building full response...")
        # Full analysis with reasoning, insights, and data
        llm = ChatGoogleGenerativeAI(
            model=text_to_sql_config.GEMINI_MODEL,
            temperature=0.1,
            max_retries=2,
            api_key=os.getenv("GEMINI_API_KEY")
        )
        prompt = create_result_interpretation_prompt(
            query=state["original_query"],
            results=state["query_results"],
            sql_query=state["generated_sql"],
        )
        insights = llm.invoke(prompt, config=run_config).content

        # Build the reasoning section without checkmarks
        reasoning_log = state.get("reasoning_log", [])
        reasoning_html = "<h4>Reasoning Process</h4><ul>"
        for step in reasoning_log:
            step_name = step.get('step_name', 'Unknown Step')
            step_details = step.get('summary', step.get('details', 'No details provided'))
            reasoning_html += f"<li><strong>{step_name}:</strong> {step_details}</li>"
        reasoning_html += "</ul>"
        
        # Add the disclaimer about the row limit
        reasoning_html += (
            "<p><small><strong>Note:</strong> To ensure a fast response, this query automatically returns a "
            "maximum of 50 rows. To view all results, you can copy the generated SQL query, "
            "remove the `LIMIT 50` clause, and run it directly against the database.</small></p>"
        )

        # Convert query results to a styled HTML table
        data_table_html = _format_table_as_html(state["query_results"])

        # ADD: Include metadata at the bottom
        confidence_score = state.get("confidence_score", 0.0)
        execution_time = state.get("execution_time_ms", 0.0)
        row_count = len(state.get("query_results", []))
        
        metadata_html = f"""
<hr/>
<div style="font-size: 0.9em; color: #666; margin-top: 20px;">
<p><strong>System:</strong> Text-to-SQL Pipeline</p>
<p><strong>Confidence Score:</strong> {confidence_score:.2f}</p>
<p><strong>Execution Time:</strong> {execution_time:.2f}ms</p>
<p><strong>Rows Returned:</strong> {row_count}</p>
</div>
"""

        final_response_str = f"""
{insights}
<h4>SQL Query Used</h4>
<pre><code>{state['generated_sql']}</code></pre>
{reasoning_html}
<br/>
{data_table_html}
{metadata_html}
"""
    else:
        logger.info("🔍 Taking DATA-ONLY path - just showing table...")
        # Data-only view
        data_table_html = _format_table_as_html(state["query_results"])
        final_response_str = data_table_html

    # Convert the entire response from Markdown to HTML
    final_response_html = _simple_markdown_to_html(final_response_str)

    logger.info(f"🔍 Final response length: {len(final_response_html)}")
    logger.info(f"🔍 Response starts with: {final_response_html[:100]}...")

    return {"final_response": final_response_html}


def _format_success_response_with_llm(
    llm: ChatGoogleGenerativeAI,
    original_query: str, 
    sql_query: str, 
    results: List[Dict],
    execution_time_ms: float,
    row_count: int,
    include_reasoning: bool
) -> str:
    """Format successful response using LLM and prompts from prompts.py."""
    
    # First, use LLM to interpret the results
    interpretation_prompt = create_result_interpretation_prompt(
        original_query, results, sql_query
    )
    
    interpretation_response = llm.invoke(interpretation_prompt)
    llm_interpretation = interpretation_response.content
    
    # Then format using the agent response template
    metadata = {
        'complexity': 'medium',  # Could be derived from query_plan if available
        'tables_used': _extract_tables_from_sql(sql_query),
        'execution_time_ms': execution_time_ms,
        'confidence_score': 0.85,  # Could be calculated based on validation results
    }
    
    # Use the format_agent_response function from prompts.py
    formatted_response = format_agent_response(
        original_query=original_query,
        results=results,
        sql_query=sql_query,
        metadata=metadata,
        include_technical_details=include_reasoning
    )
    
    # Enhance with LLM interpretation
    enhanced_response = f"""{formatted_response}

## AI Analysis
{llm_interpretation}"""
    
    return enhanced_response


def _format_error_response_with_llm(
    llm: ChatGoogleGenerativeAI,
    original_query: str,
    sql_query: str,
    error: str
) -> str:
    """Format error response using LLM and error analysis prompt."""
    
    error_prompt = ERROR_ANALYSIS_PROMPT.format(
        original_query=original_query,
        sql_query=sql_query,
        error_message=error
    )
    
    error_response = llm.invoke(error_prompt)
    return error_response.content


def _format_no_results_response_with_llm(
    llm: ChatGoogleGenerativeAI,
    original_query: str
) -> str:
    """Format no results response using LLM."""
    
    no_results_prompt = f"""The user asked: "{original_query}"

The query executed successfully but returned no results. 

Provide a helpful response that:
1. Acknowledges that no data was found
2. Explains possible reasons why
3. Suggests what the user could try next
4. Maintains a helpful and supportive tone

Keep it concise and actionable."""
    
    response = llm.invoke(no_results_prompt)
    return response.content


def _extract_tables_from_sql(sql_query: str) -> List[str]:
    """Extract table names from SQL query (simple heuristic)."""
    # This is a simple approach - could be made more sophisticated
    import re
    
    # Look for FROM and JOIN clauses
    pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    matches = re.findall(pattern, sql_query.upper())
    return list(set(matches)) if matches else ['unknown']


def _create_response_metadata(state: TextToSQLState) -> Dict[str, Any]:
    """Create response metadata."""
    return {
        "query_executed": state.get("generated_sql", "") != "",
        "results_count": len(state.get("query_results", [])),
        "execution_time_ms": state.get("execution_time_ms"),
        "has_error": state.get("execution_error") is not None,
        "timestamp": _get_timestamp()
    }


def _get_timestamp() -> str:
    """Get current timestamp."""
    from datetime import datetime
    return datetime.now().isoformat()