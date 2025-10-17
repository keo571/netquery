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
from setup.create_data_sqlite import create_infrastructure_database

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


@mcp.tool(description="Query network infrastructure: load balancers, VIPs, SSL certs, backend servers, metrics. Automatically generates charts for time-series and aggregated data.")
async def text_to_sql(
    query: str,
    show_explanation: bool = False,
    export_csv: bool = False,
    export_html: bool = False
) -> str:
    """Query network infrastructure data using natural language.

    Args:
        query: Natural language query about infrastructure (load balancers, servers, VIPs, etc.)
        show_explanation: Show detailed explanations of SQL generation and results
        export_csv: Export results to CSV file
        export_html: Generate HTML report with charts and visualizations
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
        "show_explanation": show_explanation,
        "export_csv": export_csv,
        "export_html": export_html
    }

    try:
        result = await text_to_sql_graph.ainvoke(initial_state)
        return result.get("formatted_response", "No results generated")
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        return f"Error processing query: {e}"


@mcp.tool(description="Get network infrastructure database schema: tables, columns, relationships, row counts. Use before queries to understand data model.")
def get_schema(table_names: Optional[List[str]] = None, include_sample_data: bool = False) -> str:
    """Get database schema and table information.
    
    Args:
        table_names: Specific tables to describe (optional, defaults to all tables)
        include_sample_data: Include 3 sample rows per table to understand data format
    """
    # Get tables to describe
    if table_names is not None and len(table_names) > 0:
        # Validate that the requested tables exist
        all_tables = db_toolkit.get_table_names()
        valid_tables = []
        invalid_tables = []

        for table in table_names:
            if table in all_tables:
                valid_tables.append(table)
            else:
                invalid_tables.append(table)

        if invalid_tables:
            logger.warning(f"Invalid table names: {invalid_tables}")

        tables_to_show = valid_tables

        # If no valid tables found, show available tables
        if not valid_tables:
            output = ["## Database Schema\n"]
            output.append("**Invalid table names provided.** Available tables are:\n")
            for table in all_tables:
                output.append(f"• {table}")
            return "\n".join(output)
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


@mcp.tool(description="Get suggested queries for common network operations: troubleshooting, performance, security, capacity planning")
def suggest_queries(category: Optional[str] = None) -> str:
    """Get example queries for network infrastructure monitoring.
    
    Args:
        category: Query category (troubleshooting, performance, security, capacity)
    """
    queries = {
        "troubleshooting": [
            "Show me all unhealthy load balancers",
            "Which backend servers are down in datacenter us-east-1?",
            "List VIPs with no healthy backends",
            "Show recent state changes for load balancer lb-prod-01"
        ],
        "performance": [
            "What's the average response time by datacenter?",
            "Show top 10 load balancers by traffic volume",
            "Display CPU utilization trends over the last 24 hours",
            "Which servers have memory usage above 80%?"
        ],
        "security": [
            "Which SSL certificates expire in the next 30 days?",
            "List all VIPs without valid SSL certificates",
            "Show load balancers with outdated TLS versions",
            "Which certificates are self-signed?"
        ],
        "capacity": [
            "What's the current capacity utilization by datacenter?",
            "Show growth trends for bandwidth usage",
            "List load balancers near connection limits",
            "Which datacenters need capacity expansion?"
        ]
    }
    
    if category:
        category_lower = category.lower()
        if category_lower in queries:
            output = f"## {category.capitalize()} Queries\n\n"
            for query in queries[category_lower]:
                output += f"• {query}\n"
        else:
            # Invalid category - show available categories
            output = f"## Invalid Category: '{category}'\n\n"
            output += "**Available categories:**\n"
            for cat in queries.keys():
                output += f"• {cat}\n"
    else:
        output = "## Suggested Query Categories\n\n"
        for cat, examples in queries.items():
            output += f"### {cat.capitalize()}\n"
            for query in examples[:2]:  # Show 2 examples per category
                output += f"• {query}\n"
            output += "\n"
    
    return output


def run_server():
    """Run the FastMCP server."""
    logger.info("Starting Netquery FastMCP Server")
    
    # Ensure database exists
    ensure_database()
    
    # Run server - FastMCP handles the event loop
    mcp.run()


if __name__ == "__main__":
    run_server()
