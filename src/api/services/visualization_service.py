"""
Visualization generation service for API responses.
Handles chart configuration, data processing for visualizations, and LLM-powered chart decisions.
"""
import json
import logging
from typing import Dict, List, Any, Optional

from src.text_to_sql.utils.llm_utils import get_llm
from .data_utils import apply_backend_grouping, format_data_for_display, analyze_data_patterns

logger = logging.getLogger(__name__)


def _extract_json_from_response(response: str) -> str:
    """Extract JSON content from LLM response, removing markdown code blocks if present."""
    response_text = response.strip()
    if response_text.startswith("```"):
        lines = response_text.split('\n')
        return '\n'.join(lines[1:-1])
    return response_text


async def generate_visualization(query: str, data: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Enhanced visualization generation with backend data processing.
    Handles grouping, formatting, and chart-specific calculations.
    """
    try:
        if not data or len(data) < 2:
            return None

        # Analyze data patterns
        patterns = analyze_data_patterns(data)
        columns = list(data[0].keys())
        cardinality_analysis = patterns['cardinality_analysis']
        high_card_cols = patterns['high_card_cols']
        low_card_cols = patterns['low_card_cols']
        numeric_cols = patterns['numeric_cols']
        categorical_cols = patterns['categorical_cols']

        # Check if data is already grouped (has aggregation columns like 'count')
        has_count_column = 'count' in columns
        aggregation_columns = [col for col in columns if col.lower() in ['count', 'sum', 'avg', 'total', 'amount']]
        data_already_grouped = has_count_column or len(aggregation_columns) > 0

        # Single LLM call for visualization decision
        grouping_note = ""
        if data_already_grouped:
            grouping_note = f"""
IMPORTANT: Data appears to be already grouped/aggregated (has columns: {aggregation_columns or ['count']}).
Do NOT enable frontend grouping - use the data as-is."""

        prompt = f"""Create optimal visualization for this query and data:

QUERY: "{query}"
DATA: {len(data)} rows

COLUMNS & PATTERNS:
{chr(10).join([f"- {col}: {info['unique_count']} unique values {info['sample_values']} ({info['data_type']})" for col, info in cardinality_analysis.items()])}

DETECTED PATTERNS:
- High cardinality (many items): {high_card_cols}
- Low cardinality (categories): {low_card_cols}
- Numeric columns: {numeric_cols}
- Categorical columns: {categorical_cols}
- Data already grouped: {data_already_grouped}{grouping_note}

CHART STRATEGY:
1. If data already has numeric columns (count, sum, etc.) → Use directly for bar/line charts
2. If only categorical data → Enable grouping to count occurrences for pie/bar charts
3. **PIE CHARTS are BEST for status/category distributions** - use when showing proportions
4. Bar charts for comparing quantities across categories
5. For status queries: prefer PIE charts over bar charts
6. Return "none" only if data truly cannot be visualized meaningfully

GROUPING RULES & QUERY INTENT:
- Enable grouping when: no numeric columns AND have categorical data suitable for counting
- **Distribution queries** ("status distribution", "what is the status") → group by STATUS → PIE CHART
- **Per-item queries** ("each load balancer", "show me each") → group by NAME → BAR CHART
- PIE charts: "What % are healthy vs unhealthy?" (status proportions)
- BAR charts: "Which LBs have most issues?" (comparison across items)
- Default for status data: PIE CHART unless query specifically asks about individual items

TASK: Design the best visualization considering:
1. Chart type (bar/line/pie/scatter/none)
2. Data types and whether grouping is needed
3. Pie charts for categorical distributions, bar charts for counts
4. Enable grouping when raw categorical data needs counting

RESPONSE (JSON only):
{{
    "type": "bar|line|pie|scatter|none",
    "title": "Chart title",
    "config": {{
        "x_column": "column_for_x_axis",
        "y_column": "column_for_y_axis_or_count_if_grouping",
        "reason": "Why this visualization works best",
        "grouping": {{
            "enabled": true_if_raw_categorical_data_needs_counting,
            "group_by_column": "column_to_group_by_if_enabled",
            "original_column": "original_column_if_grouping"
        }}
    }}
}}

If no chart needed, return {{"type": "none"}}.
"""

        # Get LLM decision
        llm = get_llm()
        response = await llm.ainvoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse and validate response
        try:
            response_text = _extract_json_from_response(response_text)
            viz_config = json.loads(response_text)

            if viz_config.get("type") == "none":
                return None

            # Validate required fields
            config = viz_config.get("config", {})
            x_col = config.get("x_column")

            if not x_col or x_col not in columns:
                return None

            # Process data based on grouping requirements
            chart_data = data
            grouping = config.get("grouping", {})

            if grouping.get("enabled"):
                group_col = grouping.get("group_by_column")
                original_col = grouping.get("original_column")

                if group_col and group_col in columns:
                    # Apply backend grouping
                    chart_data = apply_backend_grouping(data, group_col, original_col)
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

            # Format data for better display
            chart_data = format_data_for_display(chart_data)

            return {
                "type": chart_type,
                "title": viz_config.get("title", "Chart"),
                "config": config,
                "data": chart_data  # Include processed data
            }

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse visualization config: {e}")
            return None

    except Exception as e:
        logger.error(f"Error in visualization generation: {e}")
        return None
