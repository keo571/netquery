"""
Interpreter node for Text-to-SQL pipeline.
"""
from typing import Dict, Any, List, Optional
import logging
import time

from ..state import TextToSQLState
from ...prompts._shared import create_interpretation_prompt
from ...utils.llm_utils import get_llm
from ...utils.chart_generator import generate_chart
from ...utils.html_exporter import export_to_html
from ....common.constants import (
    LARGE_RESULT_SET_THRESHOLD,
    STATUS_WARNING,
    ICON_CSV,
    ICON_HTML
)

logger = logging.getLogger(__name__)


def _format_performance_warning(row_count: int) -> str:
    """
    Generate performance warning for large result sets.

    Args:
        row_count: Number of rows in the result set

    Returns:
        Warning message if count exceeds threshold, empty string otherwise
    """
    if row_count > LARGE_RESULT_SET_THRESHOLD:
        return f"\n{STATUS_WARNING}  **Large result set**: {row_count:,} rows returned. Consider adding filters to improve performance."
    return ""


def _export_to_html_if_enabled(state: TextToSQLState, formatted_response: str,
                                chart_html: str = None) -> Optional[str]:
    """
    Export results to HTML if enabled in state.

    Args:
        state: Pipeline state dictionary
        formatted_response: The formatted markdown response
        chart_html: Optional chart HTML content

    Returns:
        HTML export path if successful, None otherwise
    """
    if not state.get("export_html", False):
        return None

    try:
        return export_to_html(
            query=state["original_query"],
            response=formatted_response,
            chart_html=chart_html
        )
    except Exception as e:
        logger.error(f"HTML export failed: {e}")
        return None


def interpreter(state: TextToSQLState) -> Dict[str, Any]:
    """
    Format final response with query results and optional LLM insights.

    Routes to either full response (with reasoning/chart/HTML) or simple response
    based on show_explanation flag. Handles pre-set error responses.

    Args:
        state: Current pipeline state with query_results and show_explanation flag

    Returns:
        Dict with formatted_response and optional chart_html/csv_export_path
    """
    # Check for pre-set response from error handling
    if state.get("final_response"):
        return {"formatted_response": state["final_response"]}

    if state["show_explanation"]:
        return _create_full_response(state)
    else:
        return _create_simple_response(state)


def _create_simple_response(state: TextToSQLState) -> Dict[str, Any]:
    """
    Create simple response without reasoning or LLM insights.

    Formats query results as table, generates optional chart, and exports to HTML.
    Used when show_explanation=False for faster responses.

    Args:
        state: Pipeline state with query_results

    Returns:
        Dict with formatted_response, chart_html, and csv_export_path
    """
    query_results = state["query_results"] or []
    display_results = query_results[:10]
    total_count = len(query_results)

    # Generate performance warning if needed
    performance_warning = _format_performance_warning(total_count)

    # Generate chart for visualization
    chart_html = generate_chart(query_results)

    # Format SQL section
    sql_section = _format_sql_section(state["generated_sql"])

    # Format results table
    table_section = _format_results_section(display_results, total_count)

    # Create initial formatted response for HTML export
    initial_formatted_response = f"{sql_section}{table_section}"

    # Export to HTML if enabled
    html_export_path = _export_to_html_if_enabled(state, initial_formatted_response, chart_html)

    # Final footer with export paths
    footer = _format_footer(
        total_pipeline_time=state.get("total_pipeline_time_ms", 0.0),
        row_count=total_count,
        csv_path=state.get('csv_export_path'),
        html_path=html_export_path
    )

    formatted_response = f"{sql_section}{table_section}{performance_warning}{footer}"

    return {
        "formatted_response": formatted_response,
        "chart_html": chart_html,
        "html_export_path": html_export_path
    }


def _create_full_response(state: TextToSQLState) -> Dict[str, Any]:
    """Create full response with LLM insights and reasoning."""
    # Measure interpretation time
    start_time = time.time()

    # Generate insights
    llm = get_llm()
    prompt = create_interpretation_prompt(
        query=state["original_query"],
        results=state["query_results"],
        sql_query=state["generated_sql"]
    )
    insights = llm.invoke(prompt).content
    interpretation_time_ms = (time.time() - start_time) * 1000

    # Generate chart
    chart_html = generate_chart(state["query_results"])

    # Format sections
    sql_section = _format_sql_section(state["generated_sql"])
    reasoning_section = _format_reasoning_section(state.get("reasoning_log", []))

    # Format results
    display_results = state["query_results"][:10] if state["query_results"] else []
    total_results = len(state.get("query_results", []))
    results_section = _format_results_section(display_results, total_results)

    # Generate performance warning if needed
    performance_warning = _format_performance_warning(total_results)

    # Create initial formatted response for HTML export
    initial_formatted_response = f"""{sql_section}

{reasoning_section}

{results_section}

## Analysis
{insights}"""

    # Export to HTML if enabled
    html_export_path = _export_to_html_if_enabled(state, initial_formatted_response, chart_html)

    # Final footer with HTML path if available
    footer = _format_footer(
        total_pipeline_time=state.get("total_pipeline_time_ms", 0.0),
        row_count=len(state.get("query_results", [])),
        display_count=len(display_results),
        csv_path=state.get('csv_export_path'),
        html_path=html_export_path
    )

    formatted_response = f"""{sql_section}

{reasoning_section}

{results_section}

## Analysis
{insights}

{performance_warning}{footer}"""

    return {
        "formatted_response": formatted_response,
        "interpretation_time_ms": interpretation_time_ms,
        "markdown_analysis": insights,  # Store original markdown for exports
        "chart_html": chart_html,
        "html_export_path": html_export_path
    }


# Formatting helper functions

def _format_sql_section(sql: str) -> str:
    """Format SQL query section."""
    return f"## SQL Query\n```sql\n{sql.strip()}\n```"


def _format_reasoning_section(reasoning_log: List[Dict]) -> str:
    """Format reasoning/process section."""
    reasoning_text = "## Process"
    for step in reasoning_log:
        step_name = step.get('step_name', 'Step')
        step_details = step.get('details', 'Completed')
        reasoning_text += f"\n- **{step_name}:** {step_details}"
    return reasoning_text


def _format_results_section(display_results: List[Dict], total_count: int) -> str:
    """Format results table section."""
    if total_count > 10:
        header = f"\n**Results (showing first 10 of {total_count} rows):**\n\n"
    else:
        header = ""
    
    table = _format_table_as_markdown(display_results)
    return f"{header}{table}"


def _format_footer(total_pipeline_time: float, row_count: int,
                  display_count: int = None, csv_path: str = None, html_path: str = None) -> str:
    """Format footer with timing and row count information."""
    footer_parts = []

    # Add timing if available
    if total_pipeline_time > 0:
        total_seconds = total_pipeline_time / 1000
        footer_parts.append(f"_Total time: {total_seconds:.1f}s_")

    # Add row count
    if row_count > 0:
        if display_count and row_count > display_count:
            footer_parts.append(f"_Total: {row_count} rows | Displayed: {display_count} rows_")
        else:
            footer_parts.append(f"_Total: {row_count} rows_")

    # Add CSV export path if available
    if csv_path:
        footer_parts.append(f"{ICON_CSV} **Complete data:** `{csv_path}`")

    # Add HTML export path if available
    if html_path:
        footer_parts.append(f"{ICON_HTML} **HTML report:** `{html_path}`")

    return "\n\n".join(footer_parts) if footer_parts else ""


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