"""
Common constants used across the application.
"""

# Data limits
MAX_CACHE_ROWS = 30
PREVIEW_ROWS = 30
MAX_CHART_BAR_ITEMS = 20
MAX_CHART_PIE_SLICES = 8
MAX_SCATTER_POINTS = 100
MAX_LINE_CHART_POINTS = 30

# Status and UI emoji
STATUS_SUCCESS = "✅"
STATUS_ERROR = "❌"
STATUS_WARNING = "⚠️"
ICON_CSV = "📄"
ICON_HTML = "🌐"

# Performance thresholds
LARGE_RESULT_SET_THRESHOLD = 1000

# Cache and timing configuration
CACHE_TTL_SECONDS = 600  # 10 minutes
CACHE_CLEANUP_INTERVAL_SECONDS = 60  # Check every minute
CSV_CHUNK_SIZE = 1000  # Rows per chunk for CSV streaming

# Aggregation column names (lowercase)
AGGREGATION_COLUMN_NAMES = frozenset(['count', 'sum', 'avg', 'total', 'amount'])

# Column identification
ID_COLUMN_SUFFIXES = frozenset(['_id', 'id'])
SYSTEM_TABLE_PREFIXES = ['sqlite_', 'pg_', 'information_schema']
