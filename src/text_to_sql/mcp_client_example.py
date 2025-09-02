#!/usr/bin/env python3
"""
Example MCP client to test the Text-to-SQL MCP server.
This demonstrates how to connect to and use the MCP server.
"""

import asyncio
import json
import logging
from typing import Any, Dict

from mcp.client import Client
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextToSQLClient:
    """Example client for the Text-to-SQL MCP server."""
    
    def __init__(self):
        self.client = Client("text-to-sql-client", "1.0.0")
    
    async def connect_to_server(self, server_script_path: str):
        """Connect to the MCP server via stdio."""
        # The server script will be run as a subprocess
        server_params = {
            "command": "python",
            "args": [server_script_path],
            "env": {}  # Add any required environment variables
        }
        
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize the connection
            async with self.client.connect_to_server(
                read_stream,
                write_stream
            ) as session:
                logger.info("Connected to Text-to-SQL MCP server")
                return session
    
    async def list_available_tools(self, session):
        """List all available tools from the server."""
        tools = await session.list_tools()
        logger.info(f"Available tools: {len(tools)}")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        return tools
    
    async def list_available_resources(self, session):
        """List all available resources from the server."""
        resources = await session.list_resources()
        logger.info(f"Available resources: {len(resources)}")
        for resource in resources:
            logger.info(f"  - {resource.uri}: {resource.name}")
        return resources
    
    async def execute_query(self, session, query: str, include_explanation: bool = True):
        """Execute a natural language query."""
        logger.info(f"Executing query: {query}")
        
        result = await session.call_tool(
            "text_to_sql",
            {
                "query": query,
                "include_explanation": include_explanation
            }
        )
        
        return result
    
    async def get_schema(self, session, table_names=None, include_sample_data=False):
        """Get database schema information."""
        logger.info("Getting schema information")
        
        arguments = {"include_sample_data": include_sample_data}
        if table_names:
            arguments["table_names"] = table_names
        
        result = await session.call_tool("get_schema", arguments)
        return result
    
    async def read_resource(self, session, uri: str):
        """Read a specific resource."""
        logger.info(f"Reading resource: {uri}")
        result = await session.read_resource(uri)
        return result


async def main():
    """Main function demonstrating MCP client usage."""
    client = TextToSQLClient()
    
    # Path to the MCP server script
    server_script = "mcp_server_standard.py"
    
    try:
        # Connect to the server
        session = await client.connect_to_server(server_script)
        
        # List available tools
        print("\n=== Available Tools ===")
        await client.list_available_tools(session)
        
        # List available resources
        print("\n=== Available Resources ===")
        await client.list_available_resources(session)
        
        # Example queries
        queries = [
            "Show me all load balancers with their current status",
            "Which SSL certificates are expiring in the next 30 days?",
            "What is the average CPU utilization by data center?",
            "List all VIPs in the production environment"
        ]
        
        print("\n=== Executing Sample Queries ===")
        for query in queries:
            print(f"\nQuery: {query}")
            print("-" * 50)
            result = await client.execute_query(session, query)
            print(result[0].text if result else "No result")
        
        # Get schema for specific tables
        print("\n=== Schema Information ===")
        schema = await client.get_schema(
            session,
            table_names=["load_balancers", "vips"],
            include_sample_data=True
        )
        print(schema[0].text if schema else "No schema")
        
        # Read a resource
        print("\n=== Reading Schema Resource ===")
        relationships = await client.read_resource(session, "schema://relationships")
        print(relationships)
        
    except Exception as e:
        logger.error(f"Client error: {str(e)}")
        raise


if __name__ == "__main__":
    # Run the example client
    asyncio.run(main())