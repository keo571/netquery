"""
Text-to-SQL Pipeline Package
Advanced natural language to SQL conversion with safety validation and optimization.
"""

from .pipeline.graph import text_to_sql_graph as graph
from .config import config
# Use mcp_server_standard.py for MCP implementation

__version__ = "1.0.0"
__author__ = "QW the SQL Sorceress"
__description__ = "Advanced Text-to-SQL pipeline with natural language processing capabilities"

__all__ = [
    "graph",
    "config"
]

# Package metadata
PACKAGE_INFO = {
    "name": "text_to_sql",
    "version": __version__,
    "description": __description__,
    "capabilities": [
        "natural_language_to_sql",
        "schema_analysis",
        "query_validation", 
        "sql_optimization",
        "safety_checking",
        "result_interpretation"
    ],
    "supported_databases": [
        "SQLite",
        "PostgreSQL (planned)",
        "MySQL (planned)"
    ]
}