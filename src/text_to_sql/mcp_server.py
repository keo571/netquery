#!/usr/bin/env python3
"""
Standard MCP Server implementation for Text-to-SQL.
This implements the Model Context Protocol correctly using stdio transport.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource
)

from langchain_core.messages import HumanMessage

# Import the existing Text-to-SQL graph and tools
from .pipeline.graph import text_to_sql_graph
from .tools.database_toolkit import db_toolkit
from .tools.schema_inspector import schema_inspector
from .tools.safety_validator import safety_validator
from .create_sample_data import create_infrastructure_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextToSQLMCPServer:
    """
    Standard MCP Server for Text-to-SQL operations.
    
    This server exposes a single tool that handles the entire Text-to-SQL pipeline:
    1. Schema analysis
    2. Query planning
    3. SQL generation
    4. Safety validation
    5. Query execution
    6. Result formatting
    """
    
    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("text-to-sql-server")
        self.agent_graph = text_to_sql_graph
        
        # Ensure sample database exists
        self._ensure_sample_database()
        
        # Register handlers
        self._register_handlers()
    
    def _ensure_sample_database(self):
        """Ensure sample database exists, create if needed."""
        try:
            if not db_toolkit.test_connection():
                logger.info("Creating sample database...")
                create_infrastructure_database()
                logger.info("Sample database created successfully")
        except Exception as e:
            logger.error(f"Failed to ensure sample database: {str(e)}")
    
    def _register_handlers(self):
        """Register MCP protocol handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="text_to_sql",
                    description=(
                        "Convert natural language queries to SQL and execute them against "
                        "the infrastructure database. This tool handles the entire pipeline: "
                        "schema analysis, query generation, validation, and execution."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query about infrastructure data"
                            },
                            "include_explanation": {
                                "type": "boolean",
                                "description": "Include detailed explanation of SQL generation process",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_schema",
                    description="Get database schema information for understanding available tables and relationships",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific tables to get schema for (optional, returns all if not specified)"
                            },
                            "include_sample_data": {
                                "type": "boolean",
                                "description": "Include sample data rows for each table",
                                "default": False
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            if name == "text_to_sql":
                result = await self._handle_text_to_sql(arguments)
            elif name == "get_schema":
                result = await self._handle_get_schema(arguments)
            else:
                result = f"Unknown tool: {name}"
            
            return [TextContent(type="text", text=str(result))]
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri="schema://infrastructure",
                    name="Infrastructure Database Schema",
                    description="Complete schema of the infrastructure monitoring database",
                    mimeType="text/plain"
                ),
                Resource(
                    uri="schema://relationships",
                    name="Table Relationships",
                    description="Foreign key relationships between database tables",
                    mimeType="text/plain"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a resource."""
            if uri == "schema://infrastructure":
                return self._get_full_schema()
            elif uri == "schema://relationships":
                return self._get_relationships()
            else:
                return f"Unknown resource: {uri}"
    
    async def _handle_text_to_sql(self, arguments: Dict[str, Any]) -> str:
        """
        Handle text-to-SQL conversion and execution.
        
        This encapsulates the entire pipeline:
        1. Analyze the natural language query
        2. Understand the database schema
        3. Generate SQL query
        4. Validate for safety
        5. Execute the query
        6. Format and return results
        """
        query = arguments.get("query", "")
        include_explanation = arguments.get("include_explanation", True)
        
        if not query:
            return "Error: No query provided"
        
        try:
            logger.info(f"Processing text-to-SQL request: {query[:100]}...")
            
            # Create state for the agent graph
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "original_query": query,
                "natural_language_query": query,
                "include_reasoning": include_explanation,
                "validation_errors": []
            }
            
            # Run the agent graph - this handles the entire pipeline internally
            result = await self.agent_graph.ainvoke(initial_state)
            
            # Format the response
            response_parts = []
            
            # Add the main response
            response_parts.append("## Query Result\n")
            response_parts.append(result.get("formatted_response", "No results generated"))
            
            # Add explanation if requested
            if include_explanation and result.get("generated_sql"):
                response_parts.append("\n## SQL Explanation\n")
                response_parts.append(f"**Generated SQL:**\n```sql\n{result.get('generated_sql', '')}\n```\n")
                
                if result.get("sql_explanation"):
                    response_parts.append(f"**Explanation:** {result.get('sql_explanation', '')}\n")
                
                if result.get("confidence_score"):
                    response_parts.append(f"**Confidence Score:** {result.get('confidence_score', 0):.2f}\n")
                
                if result.get("relevant_tables"):
                    response_parts.append(f"**Tables Used:** {', '.join(result.get('relevant_tables', []))}\n")
            
            # Add any errors or warnings
            if result.get("execution_error"):
                response_parts.append(f"\n⚠️ **Error:** {result.get('execution_error')}\n")
            
            if result.get("validation_errors"):
                response_parts.append("\n⚠️ **Validation Issues:**\n")
                for error in result.get("validation_errors", []):
                    response_parts.append(f"- {error}\n")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Text-to-SQL processing failed: {str(e)}")
            return f"Error processing query: {str(e)}"
    
    async def _handle_get_schema(self, arguments: Dict[str, Any]) -> str:
        """Handle schema information requests."""
        table_names = arguments.get("table_names")
        include_sample_data = arguments.get("include_sample_data", False)
        
        try:
            if table_names:
                # Get specific tables
                schema_info = {}
                for table_name in table_names:
                    table_info = schema_inspector.get_table_info(table_name, include_sample_data)
                    if table_info:
                        schema_info[table_name] = self._format_table_info(table_info, include_sample_data)
            else:
                # Get all tables
                all_tables = schema_inspector.get_all_tables_info(include_sample_data)
                schema_info = {
                    table_name: self._format_table_info(table_info, include_sample_data)
                    for table_name, table_info in all_tables.items()
                }
            
            # Format as readable text
            output = ["## Database Schema\n"]
            for table_name, info in schema_info.items():
                output.append(f"### Table: {table_name}")
                output.append(info)
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Schema retrieval failed: {str(e)}")
            return f"Error retrieving schema: {str(e)}"
    
    def _format_table_info(self, table_info, include_sample_data: bool) -> str:
        """Format table information for display."""
        lines = []
        
        # Columns
        lines.append("**Columns:**")
        for col in table_info.columns:
            pk_marker = " [PK]" if col.primary_key else ""
            nullable_marker = "" if col.nullable else " NOT NULL"
            lines.append(f"- {col.name}: {col.type}{pk_marker}{nullable_marker}")
        
        # Foreign keys
        if table_info.foreign_keys:
            lines.append("\n**Foreign Keys:**")
            for fk in table_info.foreign_keys:
                lines.append(f"- {fk.column} -> {fk.referenced_table}.{fk.referenced_column}")
        
        # Row count
        lines.append(f"\n**Row Count:** {table_info.row_count}")
        
        # Sample data
        if include_sample_data and table_info.sample_data:
            lines.append("\n**Sample Data:**")
            lines.append("```")
            for row in table_info.sample_data[:3]:
                lines.append(str(row))
            lines.append("```")
        
        return "\n".join(lines)
    
    def _get_full_schema(self) -> str:
        """Get full database schema as a resource."""
        try:
            return schema_inspector.format_schema_for_llm(include_sample_data=False)
        except Exception as e:
            return f"Error retrieving schema: {str(e)}"
    
    def _get_relationships(self) -> str:
        """Get table relationships as a resource."""
        try:
            relationships = schema_inspector.get_table_relationships()
            lines = ["## Table Relationships\n"]
            
            for rel_type, rel_list in relationships.items():
                if rel_list:
                    lines.append(f"\n### {rel_type.replace('_', ' ').title()}")
                    for rel in rel_list:
                        lines.append(f"- {rel}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving relationships: {str(e)}"
    
    async def run(self):
        """Run the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    logger.info("Starting Text-to-SQL MCP Server (Standard Implementation)")
    server = TextToSQLMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())