#!/usr/bin/env python3
"""
FastMCP Server for Text-to-SQL.
Exposes network infrastructure database queries via Model Context Protocol.
"""

import asyncio
import logging
from typing import List, Optional
from fastmcp import FastMCP
from langchain_core.messages import HumanMessage

# Import pipeline and tools
from .pipeline.graph import text_to_sql_graph
from .tools.database_toolkit import db_toolkit
from .create_sample_data import create_infrastructure_database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Netquery Text-to-SQL")


def ensure_database():
    """Create sample database if it doesn't exist."""
    try:
        if not db_toolkit.test_connection():
            logger.info("Creating sample network infrastructure database...")
            create_infrastructure_database()
            logger.info("Sample database created")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")


@mcp.tool()
async def text_to_sql(query: str) -> str:
    """Query network infrastructure data using natural language.
    
    Args:
        query: Natural language query about infrastructure (load balancers, servers, VIPs, etc.)
    """
    if not query.strip():
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
    
    # Run the multi-step pipeline
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "original_query": query,
        "include_reasoning": False,  # No flags by default
        "save_csv": False,  # No flags by default
        "html": False  # No flags by default
    }
    
    try:
        result = await text_to_sql_graph.ainvoke(initial_state)
        return result.get("formatted_response", "No results generated")
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        return f"Error processing query: {e}"


@mcp.tool()
def get_schema(table_names: Optional[List[str]] = None, include_sample_data: bool = False) -> str:
    """Get database schema and table information.
    
    Args:
        table_names: Specific tables to describe (optional)
        include_sample_data: Include sample rows
    """
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
    """Run the FastMCP server."""
    logger.info("Starting Netquery FastMCP Server")
    
    # Ensure database exists
    ensure_database()
    
    # Run server
    await mcp.run()


if __name__ == "__main__":
    asyncio.run(run_server())