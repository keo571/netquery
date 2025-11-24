"""
LLM-powered interpretation service for API responses.
Provides intelligent insights for query results.
"""
import logging
from typing import Dict, List, Any, Optional

from src.text_to_sql.utils.llm_utils import get_llm

logger = logging.getLogger(__name__)


def _is_trivial_list_query(query: str, results: List[Dict]) -> bool:
    """
    Detect if query is a trivial list that doesn't need LLM interpretation OR visualization.

    Trivial list queries:
    - Simple "show me all X" queries
    - Returns only names/identifiers (no metrics to analyze or visualize)
    - No aggregation, grouping, or analysis requested

    Returns True if both LLM and visualization would add minimal value.
    """
    if not results or len(results) == 0:
        return True  # Empty results are trivial

    query_lower = query.lower()

    # Check for simple list queries
    simple_list_patterns = [
        'show me all', 'list all', 'get all', 'display all',
        'show me the', 'list the', 'get the', 'display the',
        'what are the', 'give me all', 'display the'
    ]
    is_simple_list = any(pattern in query_lower for pattern in simple_list_patterns)

    if not is_simple_list:
        return False  # Not a simple list query

    # Check data complexity - must have no analyzable data
    columns = list(results[0].keys())

    # Check if we have any numeric columns (metrics to analyze)
    has_numeric_data = any(
        isinstance(row.get(col), (int, float))
        for row in results[:5]  # Check first 5 rows
        for col in columns
        if col not in ['id', 'uuid']  # Exclude ID columns from check
    )

    # Query is trivial ONLY if it's a simple list AND has no numeric data
    # (just names/identifiers that can't be meaningfully visualized)
    return not has_numeric_data


def select_visualization_fast(
    query: str,
    results: List[Dict],
    patterns: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fast local visualization selection (NO LLM call).

    Uses pre-computed data patterns to instantly determine the best chart type.
    This provides immediate visual feedback while interpretation runs in background.

    Args:
        query: User's natural language query
        results: Query results (list of dicts)
        patterns: Pre-computed data patterns from analyze_data_patterns()

    Returns:
        Visualization config dict with type, title, config
    """
    if not results or len(results) == 0:
        return {
            "type": "none",
            "title": "No Data",
            "config": {"reason": "No results to visualize"}
        }

    # Check if this is a trivial list query (just names, no metrics)
    # These should show as table view, not charts
    if _is_trivial_list_query(query, results):
        return {
            "type": "none",
            "title": "Data Table",
            "config": {"reason": "Simple list query - table view recommended"}
        }

    columns = list(results[0].keys())
    query_lower = query.lower()

    # Extract pattern info
    low_card_cols = patterns.get('low_card_cols', [])
    numeric_cols = patterns.get('numeric_cols', [])
    categorical_cols = patterns.get('categorical_cols', [])
    data_already_grouped = patterns.get('data_already_grouped', False)

    # TIME SERIES: Check for time-based queries or date columns
    time_keywords = [
        'over time', 'by hour', 'by day', 'by month', 'by year', 'by week',
        'trend', 'timeline', 'history', 'historical', 'change over', 'progression',
        'daily', 'weekly', 'monthly', 'hourly'
    ]
    has_time_query = any(kw in query_lower for kw in time_keywords)

    # Expanded date column detection (including common abbreviations and formats)
    date_like_cols = [c for c in columns if any(t in c.lower() for t in [
        'date', 'time', 'hour', 'day', 'month', 'year', 'week',
        'created', 'updated', 'modified', 'timestamp', 'ts', 'dt',
        '_at', '_on', 'when', 'period'
    ])]

    if has_time_query or date_like_cols:
        x_col = date_like_cols[0] if date_like_cols else columns[0]
        y_col = numeric_cols[0] if numeric_cols else columns[1] if len(columns) > 1 else columns[0]
        return {
            "type": "line",
            "title": f"{y_col} over {x_col}",
            "config": {
                "x_column": x_col,
                "y_column": y_col,
                "reason": "Time-series data detected",
                "grouping": {"enabled": False}
            }
        }

    # PIE CHART: Distribution queries with low cardinality (3-10 items)
    distribution_keywords = [
        'distribution', 'breakdown', 'proportion', 'percentage', 'what percentage',
        'break down', 'split', 'composition', 'make up', 'divided', 'share of',
        'how many of each', 'types of', 'kinds of', 'categories of'
    ]
    has_distribution_query = any(kw in query_lower for kw in distribution_keywords)

    # Relax pie chart constraints: 2-12 items (was 3-10)
    if has_distribution_query and low_card_cols and 2 <= len(results) <= 12:
        category_col = low_card_cols[0]
        value_col = numeric_cols[0] if numeric_cols else category_col

        # If data is raw categorical, enable grouping
        grouping_enabled = not data_already_grouped and not numeric_cols

        return {
            "type": "pie",
            "title": f"Distribution of {category_col}",
            "config": {
                "x_column": category_col,
                "y_column": value_col,
                "reason": f"Distribution query with {len(results)} categories",
                "grouping": {
                    "enabled": grouping_enabled,
                    "group_by_column": category_col if grouping_enabled else None,
                    "original_column": category_col if grouping_enabled else None
                }
            }
        }

    # SCATTER PLOT: Correlation/relationship queries with 2+ numeric columns
    correlation_keywords = [
        'correlation', 'relationship', 'vs', 'versus', 'compared to',
        'relate', 'correlation between', 'connection between', 'impact of'
    ]
    has_correlation_query = any(kw in query_lower for kw in correlation_keywords)

    if (has_correlation_query or len(numeric_cols) >= 2) and len(results) <= 100:
        # Use first two numeric columns for scatter plot
        x_col = numeric_cols[0] if len(numeric_cols) > 0 else columns[0]
        y_col = numeric_cols[1] if len(numeric_cols) > 1 else columns[1] if len(columns) > 1 else columns[0]

        return {
            "type": "scatter",
            "title": f"{y_col} vs {x_col}",
            "config": {
                "x_column": x_col,
                "y_column": y_col,
                "reason": "Correlation/relationship analysis with numeric data",
                "grouping": {"enabled": False}
            }
        }

    # BAR CHART: Comparison queries or data with categories + numbers
    if len(results) <= 30 and (categorical_cols or low_card_cols):
        # Pick x-axis (categorical) and y-axis (numeric)
        x_col = categorical_cols[0] if categorical_cols else low_card_cols[0] if low_card_cols else columns[0]
        y_col = numeric_cols[0] if numeric_cols else columns[1] if len(columns) > 1 else x_col

        # Enable grouping if no numeric columns (raw categorical data)
        grouping_enabled = not data_already_grouped and not numeric_cols

        return {
            "type": "bar",
            "title": f"{y_col} by {x_col}",
            "config": {
                "x_column": x_col,
                "y_column": y_col,
                "reason": "Categorical comparison (≤30 items)",
                "grouping": {
                    "enabled": grouping_enabled,
                    "group_by_column": x_col if grouping_enabled else None,
                    "original_column": y_col if grouping_enabled else None
                }
            }
        }

    # DEFAULT: No visualization if too many rows or unclear structure
    return {
        "type": "none",
        "title": "Data Table",
        "config": {
            "reason": f"Too many rows ({len(results)}) or unclear visualization structure"
        }
    }


async def get_interpretation_only(
    query: str,
    results: List[Dict],
    total_rows: Optional[int] = None,
    general_answer: Optional[str] = None
) -> str:
    """
    Get LLM-powered interpretation ONLY (no visualization decision).

    Use select_visualization_fast() separately for instant visualization.

    SMART OPTIMIZATION: Skips LLM for trivial queries that don't need analysis.

    For mixed queries, prepends the general answer before SQL interpretation.

    Args:
        query: Original natural language query
        results: Query results (list of dicts, up to 30 cached rows)
        total_rows: Total number of rows in the dataset (if known, up to 1000)
        general_answer: General answer for mixed queries (prepended to interpretation)

    Returns:
        Markdown-formatted interpretation string
    """
    try:
        # If no results, return simple message
        if not results:
            return "No data found matching your query."

        # OPTIMIZATION: Skip LLM for trivial queries
        if _is_trivial_list_query(query, results):
            row_count = len(results)
            truncated = total_rows is None or (total_rows and total_rows > row_count)

            if truncated:
                return f"Found {row_count} items (showing first {row_count} of {total_rows or 'many'})."
            else:
                return f"Found {row_count} item{'s' if row_count != 1 else ''}."

        # Check if data is truncated
        truncated = total_rows is None or (total_rows and total_rows > len(results))

        prompt = create_interpretation_only_prompt(query, results, total_rows, truncated)

        # LLM CALL for interpretation only (no visualization)
        llm = get_llm()

        # Get markdown response directly
        response = await llm.ainvoke(prompt)
        interpretation = response.content.strip()

        # Prepend general answer for mixed queries
        if general_answer:
            return f"## Answer\n\n{general_answer}\n\n---\n\n{interpretation}"

        return interpretation

    except Exception as e:
        logger.error(f"Error in LLM interpretation: {e}")

        # If there's a general answer, still return it even if interpretation failed
        if general_answer:
            return f"## Answer\n\n{general_answer}\n\n---\n\nError generating data interpretation."

        return "Error generating interpretation. Please see results above."


def create_interpretation_only_prompt(
    query: str,
    results: List[Dict],
    total_rows: Optional[int],
    truncated: bool
) -> str:
    """
    Create a prompt that requests markdown interpretation (no visualization).
    This is faster as it doesn't ask LLM to decide on visualization.
    """
    # Convert results to a readable format
    if results:
        columns = list(results[0].keys())

        results_text = "Columns: " + ", ".join(columns) + "\n\n"
        results_text += f"Data ({len(results)} rows - showing all for analysis):\n"
        for i, row in enumerate(results, 1):
            # Format row data as readable key-value pairs
            row_data = ", ".join(f"{k}={v}" for k, v in row.items())
            results_text += f"Row {i}: {row_data}\n"
    else:
        results_text = "No results returned"

    truncation_note = ""
    if truncated:
        if total_rows is not None:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from total {total_rows} rows."
        else:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from a large dataset (>1000 rows total)."

    prompt = f"""Analyze query results for a network infrastructure system and provide a concise interpretation.

Query: "{query}"
Results: {len(results)} rows{truncation_note}

{results_text}

Provide a brief, well-formatted markdown interpretation that includes:
1. A bold summary sentence directly answering the query with specific numbers
2. 2-4 key findings as a bulleted list, each with:
   - Specific values and context
   - Operational impact if relevant
   - Use **bold** for emphasis on critical values or names

Keep it concise (3-5 sentences total). Focus on actionable insights.

Example format:
**[Direct answer with number]**

Key findings:
- **Critical item**: Specific value - context/impact
- **Secondary item**: Specific value - context/impact
- Overall trend or recommendation

Your markdown interpretation:"""

    return prompt
