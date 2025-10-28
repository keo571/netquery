"""
Static SVG chart generation for query results.
"""
from typing import List, Dict, Any, Optional, Tuple
import math


def generate_chart(results: List[Dict[str, Any]]) -> str:
    """Generate appropriate static SVG chart based on data pattern."""
    if not results or len(results) < 2:
        return ""
    
    columns = list(results[0].keys())
    chart_type = _detect_chart_type(results, columns)
    
    if chart_type == "line":
        return _generate_line_chart(results, columns)
    elif chart_type == "bar":
        return _generate_bar_chart(results, columns)
    elif chart_type == "scatter":
        return _generate_scatter_chart(results, columns)
    elif chart_type == "pie":
        return _generate_pie_chart(results, columns)
    else:
        return ""


def _detect_chart_type(results: List[Dict[str, Any]], columns: List[str]) -> str:
    """Detect appropriate chart type based on data pattern."""
    # Check for timestamp column (line chart)
    timestamp_col = _find_timestamp_column(columns)
    
    # Categorize columns
    numerical_cols = _find_numerical_columns(results[0], columns)
    categorical_cols = _find_categorical_columns(results[0], columns)
    
    # Decision logic
    if timestamp_col and numerical_cols:
        return "line"  # Time-series data
    elif len(results) <= 20 and categorical_cols and numerical_cols:
        # Small dataset with categories
        if len(results) <= 8 and len(numerical_cols) == 1:
            return "pie"  # Distribution/breakdown
        else:
            return "bar"  # Comparison by category
    elif len(numerical_cols) >= 2:
        return "scatter"  # Correlation between two metrics
    elif categorical_cols and numerical_cols:
        return "bar"  # Default to bar for category+number
    else:
        return ""


def _find_timestamp_column(columns: List[str]) -> Optional[str]:
    """Find column that appears to contain timestamp data."""
    for col in columns:
        if any(keyword in col.lower() for keyword in ['timestamp', 'date', 'time']):
            return col
    return None


def _find_numerical_columns(sample_row: Dict[str, Any], columns: List[str]) -> List[str]:
    """Find columns containing numerical data."""
    numerical_cols = []
    for col in columns:
        if 'id' in col.lower():
            continue
        try:
            if sample_row[col] is not None:
                float(sample_row[col])
                numerical_cols.append(col)
        except (ValueError, TypeError):
            continue
    return numerical_cols


def _find_categorical_columns(sample_row: Dict[str, Any], columns: List[str]) -> List[str]:
    """Find columns containing categorical data."""
    categorical_cols = []
    for col in columns:
        if 'id' in col.lower():
            continue
        try:
            float(sample_row[col]) if sample_row[col] is not None else 0
        except (ValueError, TypeError):
            categorical_cols.append(col)
    return categorical_cols


def _generate_line_chart(results: List[Dict[str, Any]], columns: List[str]) -> str:
    """Generate line chart for time-series data."""
    timestamp_col = _find_timestamp_column(columns)
    if not timestamp_col:
        return ""
    
    numerical_cols = _find_numerical_columns(results[0], columns)
    numerical_cols = [col for col in numerical_cols if col != timestamp_col]
    
    if not numerical_cols:
        return ""
    
    y_col = numerical_cols[0]
    
    # Extract data points
    data_points = []
    for row in results:
        value = row[y_col]
        if value is not None:
            data_points.append(float(value))
    
    if len(data_points) < 2:
        return ""
    
    return _create_svg_line_chart(data_points, y_col, len(results))


def _generate_bar_chart(results: List[Dict[str, Any]], columns: List[str]) -> str:
    """Generate bar chart for categorical comparisons."""
    categorical_col = None
    numerical_col = None
    
    numerical_cols = _find_numerical_columns(results[0], columns)
    categorical_cols = _find_categorical_columns(results[0], columns)
    
    if categorical_cols:
        categorical_col = categorical_cols[0]
    if numerical_cols:
        numerical_col = numerical_cols[0]
    
    if not categorical_col or not numerical_col:
        return ""
    
    # Prepare data (limit to 20 bars for readability)
    bar_data = []
    for row in results[:20]:
        label = str(row[categorical_col])[:20]  # Truncate long labels
        value = float(row[numerical_col]) if row[numerical_col] is not None else 0
        bar_data.append((label, value))
    
    return _create_svg_bar_chart(bar_data, numerical_col)


def _generate_scatter_chart(results: List[Dict[str, Any]], columns: List[str]) -> str:
    """Generate scatter plot for correlations."""
    numerical_cols = _find_numerical_columns(results[0], columns)
    
    if len(numerical_cols) < 2:
        return ""
    
    x_col = numerical_cols[0]
    y_col = numerical_cols[1]
    
    # Prepare data (limit to 100 points for readability)
    scatter_data = []
    for row in results[:100]:
        x_val = float(row[x_col]) if row[x_col] is not None else 0
        y_val = float(row[y_col]) if row[y_col] is not None else 0
        scatter_data.append((x_val, y_val))
    
    return _create_svg_scatter_chart(scatter_data, x_col, y_col)


def _generate_pie_chart(results: List[Dict[str, Any]], columns: List[str]) -> str:
    """Generate pie chart for distributions."""
    categorical_col = None
    numerical_col = None
    
    numerical_cols = _find_numerical_columns(results[0], columns)
    categorical_cols = _find_categorical_columns(results[0], columns)
    
    if categorical_cols:
        categorical_col = categorical_cols[0]
    if numerical_cols:
        numerical_col = numerical_cols[0]
    
    if not categorical_col or not numerical_col:
        return ""
    
    # Prepare data (limit to 8 slices)
    pie_data = []
    for row in results[:8]:
        label = str(row[categorical_col])[:15]
        value = float(row[numerical_col]) if row[numerical_col] is not None else 0
        pie_data.append((label, value))
    
    return _create_svg_pie_chart(pie_data, numerical_col)


# SVG Creation Functions

def _create_svg_line_chart(data_points: List[float], y_label: str, total_points: int) -> str:
    """Create a simple static SVG line chart."""
    if not data_points:
        return ""
    
    # Chart dimensions
    width, height, padding = 800, 400, 60
    chart_width = width - 2 * padding
    chart_height = height - 2 * padding
    
    # Calculate scales
    min_val = min(data_points)
    max_val = max(data_points)
    val_range = max_val - min_val if max_val != min_val else 1
    
    # Sample data if too many points (max 50 for readability, matches cache limit)
    if len(data_points) > 50:
        step = len(data_points) // 50
        sampled_points = data_points[::step]
    else:
        sampled_points = data_points
    
    # Generate SVG path
    points = []
    for i, value in enumerate(sampled_points):
        x = padding + (i * chart_width / (len(sampled_points) - 1 if len(sampled_points) > 1 else 1))
        y = padding + chart_height - ((value - min_val) / val_range * chart_height)
        points.append(f"{x:.1f},{y:.1f}")
    
    path = "M" + " L".join(points)
    
    return f"""
    <div style="margin: 20px 0; text-align: center;">
        <h3 style="color: #2c3e50; margin-bottom: 10px;">{y_label} Over Time</h3>
        <svg width="{width}" height="{height}" style="border: 1px solid #e1e4e8; background: white;">
            {_create_grid_lines(width, height, padding)}
            {_create_axes(width, height, padding)}
            
            <!-- Data line -->
            <path d="{path}" fill="none" stroke="#3498db" stroke-width="2" />
            
            <!-- Y-axis labels -->
            <text x="{padding-5}" y="{padding}" text-anchor="end" font-size="12" fill="#666">{max_val:.0f}</text>
            <text x="{padding-5}" y="{height-padding}" text-anchor="end" font-size="12" fill="#666">{min_val:.0f}</text>
            
            <!-- Axis labels -->
            <text x="{width/2}" y="{height-15}" text-anchor="middle" font-size="14" fill="#333">Time →</text>
            <text x="20" y="{height/2}" text-anchor="middle" font-size="14" fill="#333" transform="rotate(-90 20 {height/2})">{y_label}</text>
            
            <!-- Info text -->
            <text x="{width-padding}" y="{padding-10}" text-anchor="end" font-size="11" fill="#999">
                {len(sampled_points)} of {total_points} points shown
            </text>
        </svg>
    </div>
    """


def _create_svg_bar_chart(bar_data: List[Tuple[str, float]], y_label: str) -> str:
    """Create a simple static SVG bar chart."""
    if not bar_data:
        return ""
    
    # Chart dimensions
    width, height, padding = 800, 400, 60
    chart_width = width - 2 * padding
    chart_height = height - 2 * padding
    
    # Calculate scales
    max_val = max(value for _, value in bar_data)
    val_range = max_val if max_val > 0 else 1
    
    # Bar dimensions
    bar_count = len(bar_data)
    bar_width = chart_width / bar_count * 0.8
    bar_spacing = chart_width / bar_count
    
    # Create bars and labels
    bars_svg = ""
    labels_svg = ""
    for i, (label, value) in enumerate(bar_data):
        x = padding + i * bar_spacing + (bar_spacing - bar_width) / 2
        bar_height = (value / val_range) * chart_height
        y = padding + chart_height - bar_height
        
        bars_svg += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="#3498db" />\n'
        
        # Add label (rotated for readability)
        label_x = x + bar_width / 2
        label_y = height - padding + 15
        labels_svg += f'<text x="{label_x:.1f}" y="{label_y}" text-anchor="start" font-size="10" fill="#666" transform="rotate(45 {label_x:.1f} {label_y})">{label}</text>\n'
    
    return f"""
    <div style="margin: 20px 0; text-align: center;">
        <h3 style="color: #2c3e50; margin-bottom: 10px;">{y_label} by Category</h3>
        <svg width="{width}" height="{height + 50}" style="border: 1px solid #e1e4e8; background: white;">
            {_create_grid_lines(width, height, padding, horizontal_only=True)}
            {_create_axes(width, height, padding)}
            
            <!-- Bars -->
            {bars_svg}
            
            <!-- Y-axis labels -->
            <text x="{padding-5}" y="{padding}" text-anchor="end" font-size="12" fill="#666">{max_val:.0f}</text>
            <text x="{padding-5}" y="{height-padding}" text-anchor="end" font-size="12" fill="#666">0</text>
            
            <!-- X-axis labels (rotated) -->
            {labels_svg}
            
            <!-- Y-axis label -->
            <text x="20" y="{height/2}" text-anchor="middle" font-size="14" fill="#333" transform="rotate(-90 20 {height/2})">{y_label}</text>
        </svg>
    </div>
    """


def _create_svg_scatter_chart(scatter_data: List[Tuple[float, float]], x_label: str, y_label: str) -> str:
    """Create a simple static SVG scatter plot."""
    if not scatter_data:
        return ""
    
    # Chart dimensions
    width, height, padding = 800, 400, 60
    chart_width = width - 2 * padding
    chart_height = height - 2 * padding
    
    # Calculate scales
    x_values = [x for x, _ in scatter_data]
    y_values = [y for _, y in scatter_data]
    
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    
    x_range = x_max - x_min if x_max != x_min else 1
    y_range = y_max - y_min if y_max != y_min else 1
    
    # Create points
    points_svg = ""
    for x_val, y_val in scatter_data:
        x = padding + ((x_val - x_min) / x_range) * chart_width
        y = padding + chart_height - ((y_val - y_min) / y_range) * chart_height
        points_svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#3498db" opacity="0.7" />\n'
    
    return f"""
    <div style="margin: 20px 0; text-align: center;">
        <h3 style="color: #2c3e50; margin-bottom: 10px;">{y_label} vs {x_label}</h3>
        <svg width="{width}" height="{height}" style="border: 1px solid #e1e4e8; background: white;">
            {_create_grid_lines(width, height, padding)}
            {_create_axes(width, height, padding)}
            
            <!-- Data points -->
            {points_svg}
            
            <!-- Axis labels -->
            <text x="{padding-5}" y="{padding}" text-anchor="end" font-size="12" fill="#666">{y_max:.0f}</text>
            <text x="{padding-5}" y="{height-padding}" text-anchor="end" font-size="12" fill="#666">{y_min:.0f}</text>
            <text x="{padding}" y="{height-padding+20}" text-anchor="start" font-size="12" fill="#666">{x_min:.0f}</text>
            <text x="{width-padding}" y="{height-padding+20}" text-anchor="end" font-size="12" fill="#666">{x_max:.0f}</text>
            
            <!-- Axis names -->
            <text x="{width/2}" y="{height-15}" text-anchor="middle" font-size="14" fill="#333">{x_label}</text>
            <text x="20" y="{height/2}" text-anchor="middle" font-size="14" fill="#333" transform="rotate(-90 20 {height/2})">{y_label}</text>
        </svg>
    </div>
    """


def _create_svg_pie_chart(pie_data: List[Tuple[str, float]], value_label: str) -> str:
    """Create a simple static SVG pie chart."""
    if not pie_data:
        return ""
    
    # Chart dimensions
    width, height = 800, 400
    cx, cy = width / 2, height / 2
    radius = min(width, height) / 3
    
    # Calculate total
    total = sum(value for _, value in pie_data)
    if total == 0:
        return ""
    
    # Colors for slices
    colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#34495e", "#95a5a6"]
    
    # Generate pie slices
    slices_svg = ""
    legend_svg = ""
    start_angle = 0
    
    for i, (label, value) in enumerate(pie_data):
        # Calculate slice angle
        slice_angle = (value / total) * 360
        end_angle = start_angle + slice_angle
        
        # Convert to radians
        start_rad = start_angle * math.pi / 180
        end_rad = end_angle * math.pi / 180
        
        # Calculate arc path
        large_arc = 1 if slice_angle > 180 else 0
        
        x1 = cx + radius * math.cos(start_rad)
        y1 = cy + radius * math.sin(start_rad)
        x2 = cx + radius * math.cos(end_rad)
        y2 = cy + radius * math.sin(end_rad)
        
        # Create path for slice
        path = f"M {cx} {cy} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large_arc} 1 {x2:.1f} {y2:.1f} Z"
        
        color = colors[i % len(colors)]
        slices_svg += f'<path d="{path}" fill="{color}" stroke="white" stroke-width="2" />\n'
        
        # Add legend
        legend_y = 50 + i * 25
        legend_svg += f'<rect x="{width - 150}" y="{legend_y}" width="15" height="15" fill="{color}" />\n'
        legend_svg += f'<text x="{width - 130}" y="{legend_y + 12}" font-size="12" fill="#333">{label}: {value:.0f}</text>\n'
        
        start_angle = end_angle
    
    return f"""
    <div style="margin: 20px 0; text-align: center;">
        <h3 style="color: #2c3e50; margin-bottom: 10px;">{value_label} Distribution</h3>
        <svg width="{width}" height="{height}" style="border: 1px solid #e1e4e8; background: white;">
            <!-- Pie slices -->
            {slices_svg}
            
            <!-- Legend -->
            {legend_svg}
        </svg>
    </div>
    """


# Helper functions for common SVG elements

def _create_grid_lines(width: int, height: int, padding: int, horizontal_only: bool = False) -> str:
    """Create grid lines for charts."""
    grid = f"""
    <!-- Grid lines -->
    <g stroke="#f0f0f0" stroke-width="1">
        <!-- Horizontal grid lines -->
        <line x1="{padding}" y1="{padding}" x2="{width-padding}" y2="{padding}" />
        <line x1="{padding}" y1="{height/2}" x2="{width-padding}" y2="{height/2}" />
        <line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" />"""
    
    if not horizontal_only:
        grid += f"""
        <!-- Vertical grid lines -->
        <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" />
        <line x1="{width/2}" y1="{padding}" x2="{width/2}" y2="{height-padding}" />
        <line x1="{width-padding}" y1="{padding}" x2="{width-padding}" y2="{height-padding}" />"""
    
    grid += "\n    </g>"
    return grid


def _create_axes(width: int, height: int, padding: int) -> str:
    """Create axes for charts."""
    return f"""
    <!-- Axes -->
    <g stroke="#333" stroke-width="2">
        <line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" />
        <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" />
    </g>"""