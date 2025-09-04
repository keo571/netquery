#!/usr/bin/env python3
"""
Simple MCP Server for Text-to-SQL.
Exposes network infrastructure database queries via Model Context Protocol.
"""

import asyncio
import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from langchain_core.messages import HumanMessage

# Import pipeline and tools
from .pipeline.graph import text_to_sql_graph
from .tools.database_toolkit import db_toolkit
from .create_sample_data import create_infrastructure_database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Initialize server
server = Server("text-to-sql-server")


def ensure_database():
    """Create sample database if it doesn't exist."""
    try:
        if not db_toolkit.test_connection():
            logger.info("Creating sample network infrastructure database...")
            create_infrastructure_database()
            logger.info("Sample database created")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="text_to_sql",
            description="Query network infrastructure data using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about infrastructure (load balancers, servers, VIPs, etc.)"
                    },
                    "include_explanation": {
                        "type": "boolean",
                        "description": "Include SQL and explanation",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_schema",
            description="Get database schema and table information",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific tables to describe (optional)"
                    },
                    "include_sample_data": {
                        "type": "boolean",
                        "description": "Include sample rows",
                        "default": False
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool: {name}")
    
    try:
        if name == "text_to_sql":
            result = await handle_query(arguments)
        elif name == "get_schema":
            result = handle_schema(arguments)
        else:
            result = f"Unknown tool: {name}"
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


async def handle_query(arguments: Dict[str, Any]) -> str:
    """Handle natural language to SQL queries."""
    query = arguments.get("query", "").strip()
    include_explanation = arguments.get("include_explanation")
    
    if not query:
        # Show available tables and examples
        tables = db_toolkit.get_table_names()
        table_list = ", ".join(tables[:8])
        if len(tables) > 8:
            table_list += f" (and {len(tables) - 8} more)"
        
        return f"""Please provide a query about your network infrastructure.

**Available tables:** {table_list}

**Example queries:**
• Show me all unhealthy load balancers
• Which SSL certificates expire in the next 30 days?
• What's the average CPU utilization by datacenter?
• List all VIP addresses in production"""

    logger.info(f"Processing query: {query[:80]}...")
    
    # Run the pipeline
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "original_query": query,
        "include_reasoning": include_explanation
    }
    
    result = await text_to_sql_graph.ainvoke(initial_state)
    
    # Format response
    response = ["## Query Result\n"]
    response.append(result.get("formatted_response", "No results generated"))
    
    if include_explanation:
        # Show tables that were analyzed (from relevance_scores)
        if result.get("relevance_scores"):
            tables = list(result.get("relevance_scores", {}).keys())
            if tables:
                response.append(f"**Tables Analyzed:** {', '.join(tables[:5])}")
                if len(tables) > 5:
                    response.append(f" (and {len(tables) - 5} more)")
    
    
    return "\n".join(response)


def handle_schema(arguments: Dict[str, Any]) -> str:
    """Handle schema information requests."""
    table_names = arguments.get("table_names")
    include_sample_data = arguments.get("include_sample_data", False)
    
    # Get tables to describe
    if table_names:
        tables_to_show = table_names
    else:
        tables_to_show = db_toolkit.get_table_names()
    
    # Build schema info
    output = ["## Database Schema\n"]
    
    for table_name in tables_to_show:
        table_info = db_toolkit.get_table_info(table_name)
        if not table_info:
            continue
            
        output.append(f"### {table_name}")
        
        # Columns
        output.append("**Columns:**")
        for col in table_info.columns:
            pk = " [PK]" if col.primary_key else ""
            null = "" if col.nullable else " NOT NULL"
            output.append(f"• {col.name}: {col.type}{pk}{null}")
        
        # Foreign keys
        if table_info.foreign_keys:
            output.append("\n**Foreign Keys:**")
            for fk in table_info.foreign_keys:
                output.append(f"• {fk.column} → {fk.referenced_table}.{fk.referenced_column}")
        
        # Row count
        output.append(f"\n**Rows:** {table_info.row_count}")
        
        # Sample data
        if include_sample_data and table_info.sample_data:
            output.append("\n**Sample Data:**")
            for i, row in enumerate(table_info.sample_data[:3], 1):
                output.append(f"{i}. {row}")
        
        output.append("")  # Blank line between tables
    
    return "\n".join(output)


async def run_server():
    """Run the MCP server."""
    logger.info("Starting Text-to-SQL MCP Server")
    
    # Ensure database exists
    ensure_database()
    
    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(run_server())