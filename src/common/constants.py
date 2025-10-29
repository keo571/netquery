"""
Common constants used across the application.
"""

# Data limits
MAX_CACHE_ROWS = 50
PREVIEW_ROWS = 50
MAX_CHART_BAR_ITEMS = 20
MAX_CHART_PIE_SLICES = 8
MAX_SCATTER_POINTS = 100
MAX_LINE_CHART_POINTS = 50

# Status and UI emoji
STATUS_SUCCESS = "✅"
STATUS_ERROR = "❌"
STATUS_WARNING = "⚠️"
ICON_CSV = "📄"
ICON_HTML = "🌐"

# Performance thresholds
LARGE_RESULT_SET_THRESHOLD = 1000

# Aggregation column names (lowercase)
AGGREGATION_COLUMN_NAMES = frozenset(['count', 'sum', 'avg', 'total', 'amount'])

# Column identification
ID_COLUMN_SUFFIXES = frozenset(['_id', 'id'])
SYSTEM_TABLE_PREFIXES = ['sqlite_', 'pg_', 'information_schema']
