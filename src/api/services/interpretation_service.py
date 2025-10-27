"""
LLM-powered interpretation service for API responses.
Provides intelligent insights for query results.
"""
import json
import logging
from typing import Dict, List, Any, Optional

from src.text_to_sql.utils.llm_utils import get_llm
from src.api.data_utils import analyze_data_patterns, apply_backend_grouping, format_data_for_display, limit_chart_data

logger = logging.getLogger(__name__)


async def get_interpretation(
    query: str,
    results: List[Dict],
    total_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get LLM-powered interpretation and visualization in ONE combined call.

    Args:
        query: Original natural language query
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

        # Check if data is truncated
        truncated = total_rows is None or (total_rows and total_rows > len(results))

        prompt = create_interpretation_prompt(query, results, total_rows, truncated)

        # SINGLE LLM CALL for both interpretation and visualization
        llm = get_llm()
        response = await llm.ainvoke(prompt)

        # Extract text content from AIMessage
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse the combined response (returns both interpretation and visualization)
        result = parse_interpretation_response(response_text, results)

        return result

    except Exception as e:
        logger.error(f"Error in LLM interpretation: {e}")
        return _get_fallback_response()


def create_interpretation_prompt(
    query: str,
    results: List[Dict],
    total_rows: Optional[int],
    truncated: bool
) -> str:
    """
    Create a prompt that requests BOTH interpretation AND visualization in one call.
    """
    # Convert results to a readable format
    if results:
        columns = list(results[0].keys())

        # Analyze data patterns for visualization recommendations
        patterns = analyze_data_patterns(results)
        cardinality_analysis = patterns['cardinality_analysis']
        high_card_cols = patterns['high_card_cols']
        low_card_cols = patterns['low_card_cols']
        numeric_cols = patterns['numeric_cols']
        categorical_cols = patterns['categorical_cols']

        # Check if data is already grouped
        aggregation_columns = [col for col in columns if col.lower() in ['count', 'sum', 'avg', 'total', 'amount']]
        data_already_grouped = len(aggregation_columns) > 0

        results_text = "Columns: " + ", ".join(columns) + "\n\n"
        results_text += f"Data ({len(results)} rows - showing first 10 for analysis):\n"
        for i, row in enumerate(results[:10], 1):
            results_text += f"Row {i}: {json.dumps(row, default=str)}\n"

        # Add data patterns info
        patterns_text = f"\n\nDATA PATTERNS:\n"
        patterns_text += f"- High cardinality (many unique items): {high_card_cols}\n"
        patterns_text += f"- Low cardinality (categories): {low_card_cols}\n"
        patterns_text += f"- Numeric columns: {numeric_cols}\n"
        patterns_text += f"- Categorical columns: {categorical_cols}\n"
        patterns_text += f"- Data already grouped/aggregated: {data_already_grouped}"
        if data_already_grouped:
            patterns_text += f" (has columns: {aggregation_columns})"
    else:
        results_text = "No results returned"
        patterns_text = ""

    truncation_note = ""
    if truncated:
        if total_rows is not None:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from total {total_rows} rows."
        else:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from a large dataset (>1000 rows total)."

    prompt = f"""Analyze query results for a network infrastructure system and provide BOTH interpretation AND visualization recommendation.

Query: "{query}"
Results: {len(results)} rows{truncation_note}

{results_text}{patterns_text}

Provide CONCISE analysis and visualization in JSON format:
{{
    "summary": "Direct 1-sentence answer to the query",
    "key_findings": [
        "Critical insight 1 (with specific values)",
        "Critical insight 2 (with specific values)",
        "Critical insight 3 (with specific values)"
    ],
    "visualization": {{
        "type": "bar|line|pie|scatter|none",
        "title": "Chart title",
        "config": {{
            "x_column": "column_for_x_axis",
            "y_column": "column_for_y_axis",
            "reason": "Why this visualization works best",
            "grouping": {{
                "enabled": true_if_raw_categorical_data_needs_counting,
                "group_by_column": "column_to_group_by_if_enabled",
                "original_column": "original_column_if_grouping"
            }}
        }}
    }}
}}

VISUALIZATION GUIDELINES:
1. If data already has numeric columns (count, sum, etc.) → Use directly for bar/line charts
2. If only categorical data → Enable grouping to count occurrences
3. PIE charts are BEST for status/category distributions - use when showing proportions
4. Bar charts for comparing quantities across categories (top 100 items if >100)
5. LINE charts for time-series data or trends over time/sequences
   - Use when x_column is a date, timestamp, or sequential identifier
   - Shows changes and patterns over time
   - Good for metrics like CPU usage over time, request counts by hour, etc.
6. For status queries: prefer PIE charts over bar charts
7. Return "type": "none" if data cannot be visualized meaningfully

GROUPING RULES:
- Enable grouping when: no numeric columns AND have categorical data suitable for counting
- Distribution queries ("status distribution") → group by STATUS → PIE CHART
- Per-item queries ("each load balancer") → group by NAME → BAR CHART
- Time-series queries ("over time", "trends", "by hour/day") → LINE CHART
- Default for status data: PIE CHART unless query asks about individual items

Keep findings actionable and specific. Focus on operational impact.
"""

    return prompt


def parse_interpretation_response(llm_response: str, results: List[Dict]) -> Dict[str, Any]:
    """Parse LLM response for BOTH interpretation AND visualization."""
    try:
        response_text = _extract_json_from_response(llm_response)
        parsed = json.loads(response_text)

        # Extract interpretation
        interpretation = {
            "summary": parsed.get("summary", "Analysis complete"),
            "key_findings": parsed.get("key_findings", [])
        }

        # Extract and process visualization
        visualization = parsed.get("visualization")

        if visualization and visualization.get("type") != "none":
            # Process visualization data (grouping, formatting, etc.)
            visualization = _process_visualization_config(visualization, results)
        else:
            visualization = None

        return {
            "interpretation": interpretation,
            "visualization": visualization
        }

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logger.error(f"JSON parsing failed: {e}")
        logger.error(f"LLM response: {llm_response[:500]}")  # Log first 500 chars
        logger.error(f"Extracted text: {_extract_json_from_response(llm_response)[:500]}")
        return {
            "interpretation": {
                "summary": "Analysis temporarily unavailable. Your data was retrieved successfully.",
                "key_findings": []
            },
            "visualization": None
        }


def _get_fallback_response() -> Dict[str, Any]:
    """Return standardized fallback response when LLM fails."""
    return {
        "interpretation": {
            "summary": "Analysis temporarily unavailable. Your data was retrieved successfully.",
            "key_findings": []
        },
        "visualization": None
    }


def _process_visualization_config(viz_config: Dict[str, Any], results: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Process and validate visualization configuration, applying backend data transformations.
    This replicates the logic from visualization_service.py.
    """
    try:
        columns = list(results[0].keys()) if results else []
        config = viz_config.get("config", {})
        x_col = config.get("x_column")

        # Validate required fields
        if not x_col or x_col not in columns:
            logger.warning(f"Invalid x_column '{x_col}' not in columns {columns}")
            return None

        # Process data based on grouping requirements
        chart_data = results
        grouping = config.get("grouping", {})

        if grouping.get("enabled"):
            group_col = grouping.get("group_by_column")
            original_col = grouping.get("original_column")

            if group_col and group_col in columns:
                # Apply backend grouping
                chart_data = apply_backend_grouping(results, group_col, original_col)
                config["y_column"] = "count"  # Always use count for grouped data

                # Disable frontend grouping since we did it on backend
                config["grouping"]["enabled"] = False

        # For pie charts, pre-calculate percentages
        chart_type = viz_config.get("type")
        if chart_type == "pie" and chart_data:
            y_column = config.get("y_column", "count")
            total = sum(float(row.get(y_column, 0)) for row in chart_data)

            for row in chart_data:
                value = float(row.get(y_column, 0))
                row['percentage'] = round((value / total * 100), 1) if total > 0 else 0

        # For bar charts, limit to top N items if there are too many
        if chart_type == "bar" and chart_data and len(chart_data) > 100:
            y_column = config.get("y_column", "count")
            if y_column:
                chart_data = limit_chart_data(chart_data, y_column, max_items=100)
            else:
                # If no y_column specified, just take first 100
                logger.warning(f"Bar chart has {len(chart_data)} items but no y_column for sorting, taking first 100")
                chart_data = chart_data[:100]

        # Format data for better display
        chart_data = format_data_for_display(chart_data)

        return {
            "type": chart_type,
            "title": viz_config.get("title", "Chart"),
            "config": config,
            "data": chart_data  # Include processed data
        }

    except Exception as e:
        logger.error(f"Error processing visualization config: {e}")
        return None


def _extract_json_from_response(response: str) -> str:
    """Extract JSON content from LLM response, removing markdown code blocks if present."""
    response_text = response.strip()

    # Handle markdown code blocks (```json ... ``` or ``` ... ```)
    if "```" in response_text:
        # Find the first opening backticks
        start = response_text.find("```")
        # Skip past the opening backticks and optional language identifier
        start = response_text.find("\n", start) + 1

        # Find the closing backticks
        end = response_text.find("```", start)

        if start > 0 and end > start:
            response_text = response_text[start:end].strip()

    return response_text


