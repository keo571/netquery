"""
Text-to-SQL Agent Package
Advanced natural language to SQL conversion with safety validation and optimization.
"""

from .agent.graph import text_to_sql_graph as graph
from .config import config
from .mcp_server import TextToSQLMCPServer, run_mcp_server

__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "Advanced Text-to-SQL agent with natural language processing capabilities"

__all__ = [
    "graph",
    "config", 
    "TextToSQLMCPServer",
    "run_mcp_server"
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