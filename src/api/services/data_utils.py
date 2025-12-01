"""
Data processing utilities for API responses.
Handles formatting and pattern analysis.
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

from src.common.constants import AGGREGATION_COLUMN_NAMES

logger = logging.getLogger(__name__)


def format_data_for_display(data: List[Dict]) -> List[Dict]:
    """Format data for better display: timestamps, decimal precision, etc."""
    if not data:
        return data

    formatted_data = []
    for row in data:
        formatted_row = {}
        for key, value in row.items():
            if value is None:
                formatted_row[key] = None
            elif isinstance(value, str) and 'T' in value and ':' in value:
                # Format timestamp: 2025-01-09T15:30:00 -> 2025-01-09 15:30:00
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    formatted_row[key] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    formatted_row[key] = value
            elif isinstance(value, float):
                # Fix decimal precision issues
                if abs(value - round(value, 2)) < 0.001:
                    formatted_row[key] = round(value, 2)
                else:
                    formatted_row[key] = round(value, 3)
            else:
                formatted_row[key] = value
        formatted_data.append(formatted_row)

    return formatted_data


def _is_pseudo_categorical_numeric(col_name: str, values: List[Any], unique_count: int) -> bool:
    """
    Detect if a numeric column is actually categorical (identifiers, not measurements).

    Examples of pseudo-categorical numeric columns:
    - Port numbers (80, 443, 8080, 8443, 3000, 9000)
    - HTTP status codes (200, 404, 500)
    - Version numbers (1, 2, 3)
    - Year-only dates when used as categories (2020, 2021, 2022)

    Args:
        col_name: Column name
        values: Sample values from the column
        unique_count: Number of unique values

    Returns:
        True if numeric column should be treated as categorical
    """
    col_lower = col_name.lower()

    # Column name patterns that indicate categorical usage
    categorical_indicators = [
        'port', 'status', 'code', 'version', 'level', 'priority',
        'rank', 'grade', 'type', 'category', 'zone', 'region'
    ]

    # If column name suggests categorical usage
    if any(indicator in col_lower for indicator in categorical_indicators):
        return True

    # Low cardinality with small integer values suggests categorical
    # (e.g., priority 1-5, status codes, version numbers)
    if unique_count <= 20:
        # Check if values are small integers (< 10000)
        try:
            numeric_values = [int(v) for v in values if isinstance(v, (int, float, str)) and str(v).replace('-', '').isdigit()]
            if numeric_values:
                max_val = max(numeric_values)
                # Small integers with low cardinality are likely categorical
                if max_val < 10000:
                    return True
        except (ValueError, TypeError):
            pass

    return False


def analyze_data_patterns(data: List[Dict]) -> Dict[str, Any]:
    """Analyze data patterns: cardinality, data types, etc."""
    if not data:
        return {}

    columns = list(data[0].keys())
    cardinality_analysis = {}

    for col in columns:
        unique_values = set(str(row.get(col, '')) for row in data)
        unique_values_list = list(unique_values)

        # Check if column contains numeric data
        sample_value = data[0].get(col, '')
        is_numeric = isinstance(sample_value, (int, float)) or (
            isinstance(sample_value, str) and
            sample_value.replace('.', '').replace('-', '').isdigit()
        )

        # Check if this is a pseudo-categorical numeric column
        if is_numeric:
            # Get actual values (not stringified) for analysis
            actual_values = [row.get(col) for row in data[:10]]  # Sample first 10 rows
            is_pseudo_categorical = _is_pseudo_categorical_numeric(
                col, actual_values, len(unique_values)
            )

            # Override is_numeric if detected as pseudo-categorical
            if is_pseudo_categorical:
                is_numeric = False
                logger.debug(f"Column '{col}' detected as pseudo-categorical (treated as categorical for visualization)")

        cardinality_analysis[col] = {
            'unique_count': len(unique_values),
            'sample_values': unique_values_list[:3],
            'is_numeric': is_numeric,
            'data_type': 'numeric' if is_numeric else 'categorical'
        }

    # Find patterns
    high_card_cols = [col for col, info in cardinality_analysis.items() if info['unique_count'] > 8]
    low_card_cols = [col for col, info in cardinality_analysis.items() if 2 <= info['unique_count'] <= 6]
    numeric_cols = [col for col, info in cardinality_analysis.items() if info['is_numeric']]
    categorical_cols = [col for col, info in cardinality_analysis.items() if not info['is_numeric']]

    # Check if data is already grouped/aggregated (has columns like 'count', 'sum', 'avg')
    data_already_grouped = any(col.lower() in AGGREGATION_COLUMN_NAMES for col in columns)

    return {
        'cardinality_analysis': cardinality_analysis,
        'high_card_cols': high_card_cols,
        'low_card_cols': low_card_cols,
        'numeric_cols': numeric_cols,
        'categorical_cols': categorical_cols,
        'data_already_grouped': data_already_grouped
    }