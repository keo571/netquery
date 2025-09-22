"""
LLM-powered interpretation service for API responses.
Provides intelligent insights and visualization suggestions for query results.
"""
import json
import logging
from typing import Dict, List, Any, Optional
from src.text_to_sql.utils.llm_utils import get_llm

logger = logging.getLogger(__name__)


async def get_interpretation(
    query: str,
    sql: str,
    results: List[Dict],
    total_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get LLM-powered interpretation for API responses.

    Args:
        query: Original natural language query
        sql: Generated SQL query
        results: Query results (list of dicts, max 100 rows from cache)
        total_rows: Total number of rows in the dataset (if known, up to 1000)

    Returns:
        Dictionary with interpretation and visualization suggestions
    """
    try:
        # If no results, return simple message
        if not results:
            return {
                "interpretation": {
                    "summary": "No data found matching your query",
                    "key_findings": []
                },
                "visualization": None
            }

        # Prepare the prompt for LLM
        # We now send ALL cached results to LLM (no sampling within cache)
        # Data is truncated if we don't have all rows
        truncated = total_rows is None or (total_rows and total_rows > len(results))

        prompt = create_interpretation_prompt(
            query=query,
            sql=sql,
            results=results,  # All cached data
            total_rows=total_rows,  # Pass directly: exact count (≤1000) or None (>1000)
            truncated=truncated
        )

        # Get LLM response
        llm = get_llm()
        response = await llm.ainvoke(prompt)

        # Extract text content from AIMessage
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse the LLM response
        return parse_interpretation_response(response_text, results)

    except Exception as e:
        logger.error(f"Error in LLM interpretation: {e}")
        # Return user-friendly response if LLM fails
        return {
            "interpretation": {
                "summary": "Analysis temporarily unavailable. Your data was retrieved successfully.",
                "key_findings": []
            },
            "visualization": None
        }


def create_interpretation_prompt(
    query: str,
    sql: str,  # Keep for potential future use in prompts
    results: List[Dict],
    total_rows: Optional[int],
    truncated: bool
) -> str:
    """
    Create a focused prompt for the LLM to interpret results.
    """
    # Convert results to a readable format
    if results:
        columns = list(results[0].keys())
        results_text = "Columns: " + ", ".join(columns) + "\n\n"
        results_text += f"Data ({len(results)} rows):\n"
        # Show ALL rows for accurate analysis
        for i, row in enumerate(results, 1):
            results_text += f"Row {i}: {json.dumps(row, default=str)}\n"
    else:
        results_text = "No results returned"

    truncation_note = ""
    if truncated:
        if total_rows is not None:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from total {total_rows} rows."
        else:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from a large dataset (>1000 rows total)."

    prompt = f"""Analyze query results for a network infrastructure system.

Query: "{query}"
Results: {len(results)} rows{truncation_note}

{results_text}

Provide CONCISE analysis in JSON format:
{{
    "summary": "Direct 1-sentence answer to the query",
    "key_findings": [
        "Critical insight 1 (with specific values)",
        "Critical insight 2 (with specific values)",
        "Critical insight 3 (with specific values)"
    ],
    "best_chart": {{
        "type": "bar|line|pie|scatter|none",
        "title": "Chart title (if applicable)",
        "x_column": "column_name (if applicable)",
        "y_column": "column_name (if applicable)",
        "reason": "Why this visualization helps (or why no chart is needed)"
    }}
}}

VISUALIZATION GUIDELINES:
- Use "none" for type if data is better displayed as a table (lists, detailed records, small datasets <5 rows)
- Use "bar" for comparisons across categories (server counts by datacenter, status distributions)
- Use "line" for trends over time (performance metrics, usage patterns)
- Use "pie" for proportions/percentages (status breakdowns, resource allocation)
- Use "scatter" for correlations (CPU vs memory usage, response time vs load)

DON'T create charts for:
- Simple lists (SSL certificates, server details, specific records)
- Small datasets (<5 items) where table is clearer
- When data doesn't show patterns, trends, or comparisons

Keep findings actionable and specific. Focus on operational impact.
"""

    return prompt


def parse_interpretation_response(llm_response: str, results: List[Dict]) -> Dict[str, Any]:
    """
    Parse the LLM response into structured format.
    """
    try:
        # Extract JSON (handle markdown code blocks if present)
        response_text = llm_response.strip()
        if response_text.startswith("```"):
            # Remove markdown code blocks
            lines = response_text.split('\n')
            # Remove first and last lines (``` markers)
            response_text = '\n'.join(lines[1:-1])

        # Parse JSON
        parsed = json.loads(response_text)

        # Always return interpretation if we got this far
        interpretation = {
            "summary": parsed.get("summary", "Analysis complete"),
            "key_findings": parsed.get("key_findings", [])
        }

        # Try to build visualization, but don't fail if it doesn't work
        visualization = None
        try:
            columns_available = list(results[0].keys()) if results else []
            best_chart = parsed.get("best_chart")
            if best_chart:
                x_col = best_chart.get("x_column")
                y_col = best_chart.get("y_column")

                # Validate columns exist in data
                if x_col in columns_available and (not y_col or y_col in columns_available):
                    visualization = {
                        "type": best_chart.get("type", "bar"),
                        "title": best_chart.get("title", "Chart"),
                        "config": {
                            "x_column": x_col,
                            "y_column": y_col,
                            "reason": best_chart.get("reason", "")
                        }
                    }
        except Exception:
            # If visualization fails, just set to None but keep interpretation
            visualization = None

        return {
            "interpretation": interpretation,
            "visualization": visualization
        }

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logger.error(f"JSON parsing failed: {e}")
        # Return user-friendly response if parsing fails
        return {
            "interpretation": {
                "summary": "Analysis temporarily unavailable. Your data was retrieved successfully.",
                "key_findings": []
            },
            "visualization": None
        }




