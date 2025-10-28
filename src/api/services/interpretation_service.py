"""
LLM-powered interpretation service for API responses.
Provides intelligent insights for query results.
"""
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterable

from src.text_to_sql.utils.llm_utils import get_llm
from src.api.data_utils import analyze_data_patterns, apply_backend_grouping, format_data_for_display, limit_chart_data
from src.api.services.interpretation_schema import InterpretationResponse

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
        results: Query results (list of dicts, max 50 rows from cache)
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
        # Use structured output with Pydantic schema for guaranteed valid JSON
        llm = get_llm()
        structured_llm = llm.with_structured_output(InterpretationResponse)

        response: InterpretationResponse = await structured_llm.ainvoke(prompt)

        # Convert Pydantic model to dict and process visualization
        result = process_structured_response(response, results)

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
4. Bar charts for comparing quantities across categories (maximum 50 items due to cache limit)
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


def process_structured_response(response: InterpretationResponse, results: List[Dict]) -> Dict[str, Any]:
    """
    Process structured LLM response (Pydantic model) into final format.
    No JSON parsing needed - structured output guarantees valid data!
    """
    try:
        # Extract interpretation (already validated by Pydantic)
        interpretation = {
            "summary": response.summary,
            "key_findings": response.key_findings
        }

        # Extract and process visualization
        visualization = None
        if response.visualization and response.visualization.type != "none":
            # Only process if we have a valid config
            if not response.visualization.config:
                logger.warning(f"Visualization type '{response.visualization.type}' specified but no config provided, skipping")
            else:
                # Convert Pydantic model to dict for processing
                viz_dict = {
                    "type": response.visualization.type,
                    "title": response.visualization.title,
                    "config": response.visualization.config.model_dump()
                }
                # Process visualization data (grouping, formatting, etc.)
                visualization = _process_visualization_config(viz_dict, results)

        return {
            "interpretation": interpretation,
            "visualization": visualization
        }

    except (KeyError, AttributeError) as e:
        logger.error(f"Error processing structured response: {e}")
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
        config = viz_config.get("config")

        # Defensive check: config must exist and be a dict
        if not config or not isinstance(config, dict):
            logger.warning(f"Invalid or missing config in visualization: {viz_config}")
            return None

        x_col = config.get("x_column")

        # Validate required fields
        if not x_col:
            logger.warning(f"Missing required x_column in visualization config. Available columns: {columns}")
            return None

        if x_col not in columns:
            logger.warning(f"Invalid x_column '{x_col}' not in available columns {columns}. Skipping visualization.")
            return None

        if isinstance(x_col, str) and _column_name_has_identifier_hint(x_col):
            logger.warning(
                f"Visualization config uses identifier-like column '{x_col}' for x-axis. Skipping visualization."
            )
            return None

        # Process data based on grouping requirements
        chart_data = results
        grouping = config.get("grouping")
        if grouping is None:
            grouping = {}
            config["grouping"] = grouping
        elif hasattr(grouping, "model_dump"):
            grouping = grouping.model_dump()
            config["grouping"] = grouping
        elif not isinstance(grouping, dict):
            logger.warning(f"Invalid grouping config type '{type(grouping)}'. Skipping visualization.")
            return None

        if grouping.get("enabled"):
            group_col = grouping.get("group_by_column")
            original_col = grouping.get("original_column")

            if group_col and group_col in columns:
                # Apply backend grouping with 50 item limit (matches cache size)
                chart_data = apply_backend_grouping(results, group_col, original_col, max_items=50)

                # Update config to match grouped data structure
                config["x_column"] = group_col  # X is now the group_by column
                config["y_column"] = "count"     # Y is always count for grouped data

                # Disable frontend grouping since we did it on backend
                config["grouping"]["enabled"] = False
            else:
                # Grouping requested but column doesn't exist
                logger.warning(
                    f"Grouping requested on column '{group_col}' but not found in columns {columns}. "
                    f"Skipping visualization."
                )
                return None

        # Auto-group categorical data when LLM forgets to enable grouping but asks for counts
        chart_type = viz_config.get("type")
        y_column = config.get("y_column")
        if chart_type in {"bar", "pie"} and chart_data:
            first_row = chart_data[0]
            y_missing = not y_column or y_column not in first_row
            wants_count = (y_column or "").lower() == "count"

            if y_missing or wants_count:
                grouped = apply_backend_grouping(results, x_col, max_items=50)
                if grouped:
                    chart_data = grouped
                    config["x_column"] = x_col
                    config["y_column"] = "count"
                    config["grouping"] = {"enabled": False}
                    y_column = "count"

        # For pie charts, pre-calculate percentages
        if chart_type == "pie" and chart_data:
            y_column = config.get("y_column", "count")
            total = sum(float(row.get(y_column, 0)) for row in chart_data)

            for row in chart_data:
                value = float(row.get(y_column, 0))
                row['percentage'] = round((value / total * 100), 1) if total > 0 else 0

        # For bar charts, limit to top N items if there are too many
        # Note: With 50 row cache limit, this will rarely trigger, but kept for safety
        if chart_type == "bar" and chart_data and len(chart_data) > 50:
            y_column = config.get("y_column", "count")
            if y_column:
                chart_data = limit_chart_data(chart_data, y_column, max_items=50)
            else:
                # If no y_column specified, just take first 50
                logger.warning(f"Bar chart has {len(chart_data)} items but no y_column for sorting, taking first 50")
                chart_data = chart_data[:50]

        # Format data for better display
        chart_data = format_data_for_display(chart_data)

        # FINAL VALIDATION: Ensure x_column and y_column exist in the FINAL chart_data
        # (columns may have changed after grouping/processing)
        final_columns = list(chart_data[0].keys()) if chart_data else []
        final_x_col = config.get("x_column")
        final_y_col = config.get("y_column")

        if not final_y_col:
            inferred_y_col = _infer_numeric_column(chart_data, exclude={final_x_col})
            if inferred_y_col:
                final_y_col = inferred_y_col
                config["y_column"] = final_y_col

        if _column_looks_like_identifier(chart_data, final_x_col, chart_type):
            logger.warning(
                f"Visualization config uses identifier-like column '{final_x_col}' for x-axis. Skipping visualization."
            )
            return None

        if isinstance(final_y_col, str) and _column_name_has_identifier_hint(final_y_col):
            logger.warning(
                f"Visualization config uses identifier-like column '{final_y_col}' for y-axis. Skipping visualization."
            )
            return None

        # Validate x_column exists in final data
        if final_x_col not in final_columns:
            logger.warning(
                f"Chart validation failed: x_column '{final_x_col}' not in final data columns {final_columns}. "
                f"Skipping visualization."
            )
            return None

        # Validate y_column exists in final data (if specified)
        if final_y_col and final_y_col not in final_columns:
            logger.warning(
                f"Chart validation failed: y_column '{final_y_col}' not in final data columns {final_columns}. "
                f"Skipping visualization."
            )
            return None

        if not chart_data:
            logger.warning("Visualization has no data rows after processing; skipping chart rendering.")
            return None

        return {
            "type": chart_type,
            "title": viz_config.get("title", "Chart"),
            "config": config,
            "data": chart_data  # Include processed data
        }

    except Exception as e:
        logger.error(f"Error processing visualization config: {e}")
        return None



def _infer_numeric_column(data: List[Dict[str, Any]], exclude: Iterable[str]) -> Optional[str]:
    """Pick the first column with numeric-looking values that is not excluded."""
    if not data:
        return None

    exclude_set = set(exclude or [])
    for key in data[0].keys():
        if key in exclude_set:
            continue

        values = [row.get(key) for row in data if row.get(key) is not None]
        if not values:
            continue

        if all(_value_is_numeric(v) for v in values):
            return key

    return None


def _value_is_numeric(value: Any) -> bool:
    """Check if a value is inherently numeric or casts cleanly to float."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    return False


def _column_looks_like_identifier(data: List[Dict[str, Any]], column: Optional[str], chart_type: Optional[str]) -> bool:
    """Heuristically determine whether a column behaves like an identifier."""
    if not column or not data:
        return False

    name = column.strip()
    if not name:
        return False

    values = [row.get(column) for row in data if row.get(column) is not None]
    if not values:
        return False

    name_hint = _column_name_has_identifier_hint(name)

    # Allow time-series axes for line charts
    if chart_type == "line" and _values_look_like_time_series(values):
        return False

    # Scatter plots use numeric metrics; rely on name hints only
    if chart_type == "scatter":
        return bool(name_hint)

    unique_ratio = len({str(v) for v in values}) / max(len(values), 1)
    value_hint = _values_look_like_identifier(values)

    # Treat as identifier if name suggests it or cardinality is very high and values look like ids
    if name_hint:
        return True

    if unique_ratio >= 0.95 and value_hint:
        return True

    # For categorical charts, if we have almost unique categories, consider it identifier-like
    if chart_type in {"bar", "pie"} and unique_ratio >= 0.95 and len(values) > 20:
        return True

    return False


def _column_name_has_identifier_hint(name: str) -> bool:
    """Check column names for common identifier patterns."""
    normalized = _normalize_name_tokens(name)
    identifier_tokens = {"id", "uuid", "guid", "identifier", "key"}
    if identifier_tokens.intersection(normalized):
        return True

    # Also flag short names ending in id (e.g., "id", "nodeId")
    lowered = name.lower()
    if lowered.endswith("_id") or lowered.endswith(" id"):
        return True
    if lowered.endswith("id") and len(lowered) <= 6:
        return True

    return False


def _normalize_name_tokens(name: str) -> set:
    """Break a column name into lowercase tokens (supports camelCase, snake_case)."""
    spaced = re.sub(r"(?<!^)(?=[A-Z])", "_", name)
    tokens = re.split(r"[^a-zA-Z0-9]+", spaced.lower())
    return {token for token in tokens if token}


def _values_look_like_identifier(values: List[Any]) -> bool:
    """Detect UUID-style strings or strictly integer identifiers."""
    if not values:
        return False

    uuid_like = 0
    digit_like = 0
    int_like = 0

    for value in values:
        if isinstance(value, str):
            if _looks_like_uuid(value):
                uuid_like += 1
            elif value.isdigit():
                digit_like += 1
        elif isinstance(value, int):
            int_like += 1
        elif isinstance(value, float):
            if value.is_integer():
                int_like += 1

    total = len(values)

    if uuid_like / total >= 0.8:
        return True

    if (digit_like + int_like) / total >= 0.9 and total >= 10:
        return True

    return False


def _looks_like_uuid(value: str) -> bool:
    uuid_regex = re.compile(r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$")
    return bool(uuid_regex.match(value))


def _values_look_like_time_series(values: List[Any]) -> bool:
    """Determine if values resemble timestamps/date strings."""
    parsed = 0
    for value in values:
        if isinstance(value, datetime):
            parsed += 1
            continue
        if isinstance(value, str):
            if _parse_datetime(value):
                parsed += 1
        elif isinstance(value, (int, float)):
            # Consider numeric epochs too small to be IDs?
            if value > 10**9:
                parsed += 1

    return parsed / len(values) >= 0.8 if values else False


def _parse_datetime(value: str) -> Optional[datetime]:
    """Attempt to parse a datetime string using common formats."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None
