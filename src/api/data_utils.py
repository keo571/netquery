"""
Data processing utilities for API responses.
Handles formatting, grouping, and data transformation.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.common.constants import MAX_CACHE_ROWS

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


def apply_backend_grouping(data: List[Dict], group_by_column: str, original_column: str = None, max_items: int = MAX_CACHE_ROWS) -> List[Dict]:
    """
    Apply grouping on the backend to reduce frontend complexity.

    Args:
        data: List of data rows
        group_by_column: Column to group by
        original_column: Optional original column for tracking items
        max_items: Maximum number of groups to return (default MAX_CACHE_ROWS)

    Returns:
        List of grouped data, limited to top N by count
    """
    if not data or not group_by_column:
        return data

    groups = {}
    for row in data:
        group_key = row.get(group_by_column)
        if group_key is None:
            continue

        if group_key not in groups:
            groups[group_key] = {
                group_by_column: group_key,
                'count': 0,
                'items': []
            }

        groups[group_key]['count'] += 1
        if original_column and row.get(original_column):
            groups[group_key]['items'].append(row[original_column])

    # Convert to list and sort by count (descending)
    grouped_list = list(groups.values())
    grouped_list.sort(key=lambda x: x['count'], reverse=True)

    # Limit to max_items
    if len(grouped_list) > max_items:
        logger.info(f"Limiting visualization data from {len(grouped_list)} to {max_items} items")
        grouped_list = grouped_list[:max_items]

    return grouped_list


def limit_chart_data(data: List[Dict], y_column: str, max_items: int = MAX_CACHE_ROWS) -> List[Dict]:
    """
    Limit chart data to top N items by y_column value.

    Args:
        data: List of data rows
        y_column: Column to sort by (typically a numeric column like 'count')
        max_items: Maximum number of items to return (default MAX_CACHE_ROWS)

    Returns:
        Limited list of data, sorted by y_column descending
    """
    if not data or len(data) <= max_items:
        return data

    # Sort by y_column (descending)
    try:
        sorted_data = sorted(data, key=lambda x: float(x.get(y_column, 0)), reverse=True)
        limited_data = sorted_data[:max_items]
        logger.info(f"Limited chart data from {len(data)} to {max_items} items based on {y_column}")
        return limited_data
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not sort data by {y_column}: {e}, returning first {max_items} items")
        return data[:max_items]


def analyze_data_patterns(data: List[Dict]) -> Dict[str, Any]:
    """Analyze data patterns: cardinality, data types, etc."""
    if not data:
        return {}

    columns = list(data[0].keys())
    cardinality_analysis = {}

    for col in columns:
        unique_values = set(str(row.get(col, '')) for row in data)
        # Check if column contains numeric data
        sample_value = data[0].get(col, '')
        is_numeric = isinstance(sample_value, (int, float)) or (
            isinstance(sample_value, str) and
            sample_value.replace('.', '').replace('-', '').isdigit()
        )

        cardinality_analysis[col] = {
            'unique_count': len(unique_values),
            'sample_values': list(unique_values)[:3],
            'is_numeric': is_numeric,
            'data_type': 'numeric' if is_numeric else 'categorical'
        }

    # Find patterns
    high_card_cols = [col for col, info in cardinality_analysis.items() if info['unique_count'] > 8]
    low_card_cols = [col for col, info in cardinality_analysis.items() if 2 <= info['unique_count'] <= 6]
    numeric_cols = [col for col, info in cardinality_analysis.items() if info['is_numeric']]
    categorical_cols = [col for col, info in cardinality_analysis.items() if not info['is_numeric']]

    return {
        'cardinality_analysis': cardinality_analysis,
        'high_card_cols': high_card_cols,
        'low_card_cols': low_card_cols,
        'numeric_cols': numeric_cols,
        'categorical_cols': categorical_cols
    }