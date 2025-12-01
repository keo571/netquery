"""
LLM-powered interpretation service for API responses.
Provides intelligent insights for query results.
"""
import logging
from typing import Dict, List, Any, Optional

from src.text_to_sql.utils.llm_utils import get_llm
from src.text_to_sql.utils.query_extraction import extract_current_query

logger = logging.getLogger(__name__)


def process_visualization_data(visualization: Dict[str, Any], data: List[Dict]) -> Dict[str, Any]:
    """
    Process visualization data to perform grouping/aggregation when needed.

    When visualization.config.grouping.enabled is True, this function:
    1. Groups raw categorical data by the group_by_column
    2. Counts occurrences in each group
    3. Creates aggregated rows with a "count" column
    4. Optionally preserves originalItems array for tooltips

    Args:
        visualization: Visualization config from select_visualization_fast()
        data: Raw query results

    Returns:
        Updated visualization dict with processed data attached
    """
    if not visualization or not data or visualization.get("type") == "none":
        return visualization

    config = visualization.get("config", {})
    grouping = config.get("grouping", {})

    # Check if grouping is enabled
    if not grouping.get("enabled", False):
        return visualization

    # IMPORTANT: Only perform grouping on raw, unaggregated data
    # If data is already grouped (has count/sum columns), don't re-group it
    # Check if data already has aggregated columns like 'count', 'total', 'sum', etc.
    if data and len(data) > 0:
        first_row = data[0]
        agg_column_patterns = ['count', 'total', 'sum', 'avg', 'average', 'max', 'min']
        has_agg_column = any(
            any(pattern in col.lower() for pattern in agg_column_patterns)
            for col in first_row.keys()
        )
        if has_agg_column:
            logger.info(f"[VIZ DEBUG] Data already has aggregated columns, skipping grouping")
            return visualization

    group_by_column = grouping.get("group_by_column")
    if not group_by_column:
        logger.warning("Grouping enabled but no group_by_column specified")
        return visualization

    # Perform grouping and counting
    from collections import defaultdict

    # Log the input data to debug
    logger.info(f"[VIZ DEBUG] Input data for grouping (first 5 rows): {data[:5] if len(data) > 5 else data}")
    logger.info(f"[VIZ DEBUG] Total rows to group: {len(data)}")

    grouped_data = defaultdict(list)
    for row in data:
        category_value = row.get(group_by_column)
        if category_value is not None:
            grouped_data[category_value].append(row)

    # Create aggregated data with count column
    aggregated_data = []
    for category, items in grouped_data.items():
        aggregated_row = {
            group_by_column: category,
            "count": len(items),
            "originalItems": [item.get(group_by_column) for item in items]
        }
        aggregated_data.append(aggregated_row)

    # Sort by count descending for better visualization
    aggregated_data.sort(key=lambda x: x["count"], reverse=True)

    # Attach processed data to visualization
    visualization["data"] = aggregated_data

    logger.info(f"[VIZ DEBUG] Grouped {len(data)} rows into {len(aggregated_data)} categories")
    logger.info(f"[VIZ DEBUG] Aggregated data: {aggregated_data}")

    return visualization


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


def _select_best_y_column(query: str, numeric_cols: List[str]) -> str:
    """
    Intelligently select the best Y-axis column based on query keywords.

    Matches query terms to column names to pick the most relevant metric.
    Falls back to first column if no match found.

    Args:
        query: User's natural language query (lowercase)
        numeric_cols: List of available numeric column names

    Returns:
        Best matching column name
    """
    query_lower = query.lower()

    # Keyword-to-column mappings (order matters - more specific first)
    keyword_mappings = [
        # Bandwidth/Traffic patterns
        (['bandwidth', 'bytes', 'traffic', 'data transfer', 'throughput'], ['bytes_out', 'bytes_in', 'bytes']),

        # Request/Connection patterns
        (['request', 'rps', 'queries', 'qps'], ['requests_per_second', 'requests', 'queries_per_second']),
        (['connection', 'conn'], ['active_connections', 'connections', 'conn_count']),

        # Performance patterns
        (['latency', 'response time', 'delay'], ['latency', 'response_time', 'avg_latency']),
        (['cpu', 'processor'], ['cpu_usage', 'cpu_percent', 'cpu']),
        (['memory', 'ram'], ['memory_usage', 'memory_percent', 'ram']),

        # Health/Status patterns
        (['health', 'score'], ['health_score', 'health', 'score']),
        (['error', 'failure', 'fail'], ['error_rate', 'error_count', 'errors', 'failures']),
    ]

    # Try to find best match
    for query_keywords, column_patterns in keyword_mappings:
        # Check if query contains any of the keywords
        if any(keyword in query_lower for keyword in query_keywords):
            # Look for matching column in available columns
            for col_pattern in column_patterns:
                for col in numeric_cols:
                    if col_pattern in col.lower():
                        logger.info(f"[VIZ DEBUG] Smart column selection: '{col}' (matched query keyword)")
                        return col

    # Fallback: return first numeric column
    logger.info(f"[VIZ DEBUG] No keyword match, using first numeric column: '{numeric_cols[0]}'")
    return numeric_cols[0]


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

    # Extract actual user query from conversation context (if present)
    # This prevents "CONVERSATION HISTORY" from matching keywords like "history"
    actual_query = extract_current_query(query)

    columns = list(results[0].keys())
    query_lower = actual_query.lower()

    # Extract pattern info
    low_card_cols = patterns.get('low_card_cols', [])
    numeric_cols = patterns.get('numeric_cols', [])
    categorical_cols = patterns.get('categorical_cols', [])
    data_already_grouped = patterns.get('data_already_grouped', False)

    # Detect date/time columns based on column names and data
    date_like_cols = []
    for c in columns:
        c_lower = c.lower()
        # Check for suffix patterns (must end with these)
        if c_lower.endswith('_at') or c_lower.endswith('_on') or c_lower.endswith('_ts') or c_lower.endswith('_dt'):
            date_like_cols.append(c)
            continue
        # Check for substring patterns (anywhere in column name)
        if any(t in c_lower for t in [
            'date', 'time', 'hour', 'day', 'month', 'year', 'week',
            'created', 'updated', 'modified', 'timestamp',
            'when', 'period'
        ]):
            date_like_cols.append(c)

    # Determine chart type based on data structure first, query text as secondary signal
    # Strategy: Examine the result structure to infer the appropriate visualization

    # DEBUG LOGGING
    logger.info(f"[VIZ DEBUG] Full query (first 100 chars): '{query[:100]}...'")
    logger.info(f"[VIZ DEBUG] Extracted query: '{actual_query}'")
    logger.info(f"[VIZ DEBUG] Columns: {columns}")
    logger.info(f"[VIZ DEBUG] Numeric cols: {numeric_cols}")
    logger.info(f"[VIZ DEBUG] Date-like cols: {date_like_cols}")
    logger.info(f"[VIZ DEBUG] Low-card cols: {low_card_cols}")
    logger.info(f"[VIZ DEBUG] Row count: {len(results)}")

    # 1. TIME SERIES: Detect when query explicitly asks for time-based analysis
    # Match explicit time-series keywords OR time-range patterns (last N days/weeks/months)
    time_keywords = ['over time', 'trend', 'timeline', 'history', 'historical', 'change over', 'progression']
    time_range_patterns = ['over the last', 'over the past', 'in the last', 'in the past',
                          'during the last', 'during the past', 'within the last', 'within the past']

    has_explicit_time_query = (
        any(kw in query_lower for kw in time_keywords) or
        any(pattern in query_lower for pattern in time_range_patterns)
    )
    logger.info(f"[VIZ DEBUG] Time keywords check: {has_explicit_time_query}")

    # Only use line chart if query explicitly asks for time-based analysis
    if has_explicit_time_query:
        # Select X-axis (timestamp column)
        x_col = date_like_cols[0] if date_like_cols else columns[0]

        # Select Y-axis (numeric column, excluding timestamp columns)
        # Filter out timestamp columns from numeric_cols for Y-axis selection
        non_timestamp_numeric_cols = [col for col in numeric_cols if col not in date_like_cols]

        # Only create line chart if we have a valid numeric Y-axis
        if non_timestamp_numeric_cols:
            # SMART COLUMN SELECTION: Match Y-axis to query intent
            y_col = _select_best_y_column(actual_query, non_timestamp_numeric_cols)
            logger.info(f"[VIZ DEBUG] RETURNING LINE CHART (time-series): x={x_col}, y={y_col}")
            return {
                "type": "line",
                "title": f"{y_col} over {x_col}",
                "config": {
                    "x_column": x_col,
                    "y_column": y_col,
                    "reason": "Time-series analysis",
                    "grouping": {"enabled": False}
                }
            }
        else:
            # No valid numeric column for Y-axis - fall through to other chart types
            logger.warning(f"[VIZ DEBUG] Time-series query but no numeric Y-axis found. Falling back to other visualizations.")


    # 2. PIE CHART: Distribution queries with low cardinality (2-12 items)
    distribution_keywords = ['distribution', 'breakdown', 'proportion', 'percentage', 'share']
    has_distribution_query = any(kw in query_lower for kw in distribution_keywords)
    logger.info(f"[VIZ DEBUG] Distribution keywords check: {has_distribution_query}")
    logger.info(f"[VIZ DEBUG] Pie chart condition: has_distribution={has_distribution_query}, low_card_cols={low_card_cols}, row_count={len(results)} (need 2-12)")

    if has_distribution_query and low_card_cols and 2 <= len(results) <= 12:
        category_col = low_card_cols[0]

        # DEBUG: Log the exact columns we received
        logger.info(f"[VIZ DEBUG] Available columns in data: {columns}")
        logger.info(f"[VIZ DEBUG] First row of data: {results[0]}")

        # Check if data already has a count/aggregate column from SQL GROUP BY
        # Look for columns with names like 'count', 'cnt', 'total', 'COUNT(*)', etc.
        count_column = None
        for col in columns:
            col_lower = col.lower().replace(' ', '')  # Remove spaces
            # Direct name matches
            if col_lower in ['count', 'cnt', 'total', 'num', 'number', 'quantity']:
                count_column = col
                logger.info(f"[VIZ DEBUG] Found count column (direct): '{col}'")
                break
            # SQL function patterns like 'COUNT(*)', 'count(*)', 'COUNT(1)', etc.
            # Check if column name contains 'count' anywhere
            if 'count' in col_lower:
                count_column = col
                logger.info(f"[VIZ DEBUG] Found count column (pattern): '{col}'")
                break

        logger.info(f"[VIZ DEBUG] Final count_column: {count_column}")

        # DISABLE Python-side grouping for now - SQL should handle GROUP BY COUNT
        # The SQL generator creates proper GROUP BY queries, so we don't need to re-group
        grouping_enabled = False

        # Set y_column appropriately:
        # PRIORITY 1: Use COUNT(*) column if it exists (common SQL aggregate)
        # PRIORITY 2: Use detected count_column from our pattern matching
        # PRIORITY 3: Use first numeric column
        # Otherwise: No visualization possible
        if 'COUNT(*)' in columns:
            value_col = 'COUNT(*)'
            logger.info(f"[VIZ DEBUG] Using COUNT(*) column directly")
        elif count_column:
            value_col = count_column  # SQL already did GROUP BY COUNT
            logger.info(f"[VIZ DEBUG] Using detected count_column: {count_column}")
        elif numeric_cols:
            value_col = numeric_cols[0]
            logger.info(f"[VIZ DEBUG] Using first numeric column: {numeric_cols[0]}")
        else:
            # Data looks like distinct categories without counts - can't visualize
            # SQL should have used GROUP BY with COUNT
            logger.warning(f"[VIZ DEBUG] Pie chart requested but data has no counts (SQL returned DISTINCT without COUNT)")
            return {
                "type": "none",
                "title": "No Visualization",
                "config": {
                    "reason": "Distribution query needs aggregated counts",
                    "grouping": {"enabled": False}
                }
            }

        logger.info(f"[VIZ DEBUG] RETURNING PIE CHART (distribution), y_column={value_col}")

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

    # 3. SCATTER PLOT: Correlation/relationship queries with 2+ numeric columns
    correlation_keywords = ['correlation', 'relationship', 'vs', 'versus', 'impact']
    has_correlation_query = any(kw in query_lower for kw in correlation_keywords)
    logger.info(f"[VIZ DEBUG] Scatter plot condition: has_correlation={has_correlation_query}, numeric_cols={len(numeric_cols)}, row_count={len(results)} (need <=100)")

    if (has_correlation_query or len(numeric_cols) >= 2) and len(results) <= 100:
        # Use first two numeric columns for scatter plot
        x_col = numeric_cols[0] if len(numeric_cols) > 0 else columns[0]
        y_col = numeric_cols[1] if len(numeric_cols) > 1 else columns[1] if len(columns) > 1 else columns[0]
        logger.info(f"[VIZ DEBUG] RETURNING SCATTER PLOT")

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

    # 4. BAR CHART: Default for categorical data with numeric values (≤30 rows)
    # This catches most "Show count of X by Y" queries
    logger.info(f"[VIZ DEBUG] Bar chart condition: row_count={len(results)} (need <=30), categorical_cols={categorical_cols}, low_card_cols={low_card_cols}")
    if len(results) <= 30 and (categorical_cols or low_card_cols):
        # Pick x-axis (categorical) and y-axis (numeric)
        x_col = categorical_cols[0] if categorical_cols else low_card_cols[0] if low_card_cols else columns[0]

        # Enable grouping if no numeric columns (raw categorical data)
        grouping_enabled = not data_already_grouped and not numeric_cols

        # Set y_column appropriately:
        # - If we have numeric data, use the first numeric column
        # - If grouping is enabled (raw categorical data), use "count" as the aggregated column name
        if numeric_cols:
            y_col = numeric_cols[0]
        elif grouping_enabled:
            y_col = "count"  # Standard column name for grouped/aggregated counts
        else:
            # Fallback: try to use second column if available, otherwise x_col
            y_col = columns[1] if len(columns) > 1 else x_col

        logger.info(f"[VIZ DEBUG] RETURNING BAR CHART (default categorical)")

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
    logger.info(f"[VIZ DEBUG] RETURNING NONE (no visualization)")
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
) -> Dict[str, Any]:
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
        Dict with structured interpretation (summary, key_findings, insights)
    """
    import json

    try:
        # Extract clean query without "CONTEXT RULES" section
        # Keep conversation history but remove instruction prompts meant for SQL generation
        clean_query = query
        if "CONTEXT RULES FOR FOLLOW-UP QUESTIONS" in query:
            # Split at "CONTEXT RULES" and take everything before it
            clean_query = query.split("CONTEXT RULES FOR FOLLOW-UP QUESTIONS")[0].strip()
            logger.debug(f"Removed CONTEXT RULES section from interpretation query")

        # Use the cleaned query for interpretation
        query = clean_query

        # If no results, return simple structured response
        if not results:
            return {
                "summary": "No data found matching your query.",
                "key_findings": [],
                "recommendations": []
            }

        # OPTIMIZATION: Skip LLM for trivial queries
        if _is_trivial_list_query(query, results):
            row_count = len(results)
            truncated = total_rows is None or (total_rows and total_rows > row_count)

            if truncated:
                summary = f"Found {row_count} items (showing first {row_count} of {total_rows or 'many'})."
            else:
                summary = f"Found {row_count} item{'s' if row_count != 1 else ''}."

            return {
                "summary": summary,
                "key_findings": [],
                "recommendations": []
            }

        # Check if data is truncated
        truncated = total_rows is None or (total_rows and total_rows > len(results))

        prompt = create_interpretation_only_prompt(query, results, total_rows, truncated)

        # LLM CALL for interpretation only (no visualization)
        llm = get_llm()

        # Get JSON response from LLM
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # Try to parse JSON response
        try:
            # Remove markdown code blocks if present
            if content.startswith("```"):
                # Extract JSON from code block
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            interpretation_data = json.loads(content)

            # Validate structure
            if not isinstance(interpretation_data, dict):
                raise ValueError("LLM response is not a dict")

            # Ensure required fields exist with defaults
            result = {
                "summary": interpretation_data.get("summary", "Analysis completed."),
                "key_findings": interpretation_data.get("key_findings", []),
                "recommendations": interpretation_data.get("recommendations", [])
            }

            # Prepend general answer for mixed queries
            if general_answer:
                result["summary"] = f"{general_answer}\n\n{result['summary']}"

            return result

        except (json.JSONDecodeError, ValueError) as parse_error:
            logger.warning(f"Failed to parse LLM JSON response, falling back to string format: {parse_error}")
            # Fallback: treat the entire response as summary
            summary = content
            if general_answer:
                summary = f"{general_answer}\n\n{summary}"

            return {
                "summary": summary,
                "key_findings": [],
                "recommendations": []
            }

    except Exception as e:
        logger.error(f"Error in LLM interpretation: {e}")

        # If there's a general answer, still return it even if interpretation failed
        summary = "Error generating interpretation. Please see results above."
        if general_answer:
            summary = f"{general_answer}\n\n{summary}"

        return {
            "summary": summary,
            "key_findings": [],
            "recommendations": []
        }


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

    prompt = f"""Analyze query results for a network infrastructure system and provide a concise structured interpretation.

Query: "{query}"
Results: {len(results)} rows{truncation_note}

{results_text}

Provide your analysis as a JSON object with the following structure:
{{
  "summary": "A single sentence directly answering the query with specific numbers",
  "key_findings": [
    "First key finding with specific values and context",
    "Second key finding with operational impact if relevant",
    "Third key finding (2-4 total)"
  ],
  "recommendations": [
    "Optional actionable recommendation or trend observation"
  ]
}}

Requirements:
- summary: One concise sentence with the direct answer
- key_findings: 2-4 specific observations, each mentioning concrete values
- recommendations:0-2 actionable recommendations or broader trends (optional)
- Keep all text natural and readable (no markdown formatting needed)
- Focus on actionable insights relevant to network operations

Example:
{{
  "summary": "There are 50 load balancers across 4 datacenters, with eu-west-1 having the most at 18",
  "key_findings": [
    "eu-west-1 has 18 load balancers, the highest concentration",
    "us-west-2 has only 8 load balancers, significantly lower than others",
    "Distribution ranges from 8 to 18 load balancers per datacenter"
  ],
  "recommendations": [
    "Consider rebalancing resources if traffic distribution is similar across regions"
  ]
}}

Your JSON response:"""

    return prompt
