#!/usr/bin/env python3
"""
Enhanced MCP Server with streaming support and batch processing for Text-to-SQL.
"""

import asyncio
import logging
import sys
import json
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime
import traceback

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
from .utils.sql_utils import validate_sql_syntax, estimate_query_cost

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedTextToSQLMCPServer:
    """
    Enhanced MCP Server for Text-to-SQL operations with streaming and batch support.
    
    Features:
    - Streaming results for large datasets
    - Batch query processing
    - Query history tracking
    - Cost estimation before execution
    - Parallel query execution
    """
    
    def __init__(self):
        """Initialize the enhanced MCP server."""
        self.server = Server("text-to-sql-server-enhanced")
        self.agent_graph = text_to_sql_graph
        self.query_history: List[Dict[str, Any]] = []
        self.active_streams: Dict[str, AsyncIterator] = {}
        
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
                            },
                            "stream_results": {
                                "type": "boolean",
                                "description": "Stream results for large datasets",
                                "default": False
                            },
                            "estimate_only": {
                                "type": "boolean",
                                "description": "Only estimate query cost without execution",
                                "default": False
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="batch_queries",
                    description="Execute multiple queries in batch for better performance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "queries": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "query": {"type": "string"}
                                    },
                                    "required": ["query"]
                                },
                                "description": "List of queries to execute"
                            },
                            "parallel": {
                                "type": "boolean",
                                "description": "Execute queries in parallel",
                                "default": False
                            },
                            "stop_on_error": {
                                "type": "boolean",
                                "description": "Stop batch execution on first error",
                                "default": False
                            }
                        },
                        "required": ["queries"]
                    }
                ),
                Tool(
                    name="get_query_history",
                    description="Get history of executed queries",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of queries to return",
                                "default": 10
                            },
                            "include_results": {
                                "type": "boolean",
                                "description": "Include query results in history",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="stream_query_results",
                    description="Stream results from a previously executed query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "stream_id": {
                                "type": "string",
                                "description": "ID of the stream to read from"
                            },
                            "batch_size": {
                                "type": "integer",
                                "description": "Number of rows to return per batch",
                                "default": 100
                            }
                        },
                        "required": ["stream_id"]
                    }
                ),
                Tool(
                    name="estimate_query_cost",
                    description="Estimate the cost and complexity of a query before execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language or SQL query to estimate"
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
            
            try:
                if name == "text_to_sql":
                    result = await self._handle_text_to_sql(arguments)
                elif name == "batch_queries":
                    result = await self._handle_batch_queries(arguments)
                elif name == "get_query_history":
                    result = await self._handle_get_query_history(arguments)
                elif name == "stream_query_results":
                    result = await self._handle_stream_results(arguments)
                elif name == "estimate_query_cost":
                    result = await self._handle_estimate_cost(arguments)
                elif name == "get_schema":
                    result = await self._handle_get_schema(arguments)
                else:
                    result = f"Unknown tool: {name}"
            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                result = f"Error: {str(e)}"
            
            return [TextContent(type="text", text=str(result))]
    
    async def _handle_text_to_sql(self, arguments: Dict[str, Any]) -> str:
        """
        Handle Text-to-SQL conversion and execution with streaming support.
        """
        query = arguments.get("query", "")
        include_explanation = arguments.get("include_explanation", True)
        stream_results = arguments.get("stream_results", False)
        estimate_only = arguments.get("estimate_only", False)
        
        if not query:
            return "Error: No query provided"
        
        try:
            # First, estimate the query cost
            if estimate_only:
                cost_estimate = await self._estimate_query_cost(query)
                return json.dumps(cost_estimate, indent=2)
            
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "original_query": query,
                "natural_language_query": query,
                "include_reasoning": include_explanation,
                "validation_errors": []
            }
            
            # Run the pipeline
            result = await self.agent_graph.ainvoke(initial_state)
            
            # Track query in history
            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "sql": result.get("generated_sql", ""),
                "success": result.get("execution_error") is None,
                "row_count": len(result.get("query_results", [])) if result.get("query_results") else 0
            }
            self.query_history.append(history_entry)
            
            # Handle streaming if requested
            if stream_results and result.get("query_results"):
                stream_id = f"stream_{datetime.now().timestamp()}"
                self.active_streams[stream_id] = self._create_result_stream(result["query_results"])
                
                return json.dumps({
                    "stream_id": stream_id,
                    "total_rows": len(result["query_results"]),
                    "message": "Results are being streamed. Use stream_query_results tool to fetch batches."
                }, indent=2)
            
            # Return formatted response
            if result.get("formatted_response"):
                return result["formatted_response"]
            else:
                return json.dumps({
                    "error": result.get("execution_error", "Unknown error"),
                    "validation_errors": result.get("validation_errors", [])
                }, indent=2)
                
        except Exception as e:
            logger.error(f"Error in text_to_sql: {str(e)}")
            return f"Error processing query: {str(e)}"
    
    async def _handle_batch_queries(self, arguments: Dict[str, Any]) -> str:
        """
        Handle batch query processing with optional parallel execution.
        """
        queries = arguments.get("queries", [])
        parallel = arguments.get("parallel", False)
        stop_on_error = arguments.get("stop_on_error", False)
        
        if not queries:
            return "Error: No queries provided"
        
        results = []
        
        try:
            if parallel:
                # Process queries in parallel
                tasks = []
                for query_obj in queries:
                    task = self._process_single_query(query_obj)
                    tasks.append(task)
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=not stop_on_error)
                
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        results.append({
                            "id": queries[i].get("id", str(i)),
                            "error": str(result)
                        })
                    else:
                        results.append(result)
            else:
                # Process queries sequentially
                for query_obj in queries:
                    try:
                        result = await self._process_single_query(query_obj)
                        results.append(result)
                    except Exception as e:
                        error_result = {
                            "id": query_obj.get("id", "unknown"),
                            "error": str(e)
                        }
                        results.append(error_result)
                        
                        if stop_on_error:
                            break
            
            return json.dumps({
                "total_queries": len(queries),
                "successful": sum(1 for r in results if "error" not in r),
                "failed": sum(1 for r in results if "error" in r),
                "results": results
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            return f"Error processing batch: {str(e)}"
    
    async def _process_single_query(self, query_obj: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single query and return results."""
        query_id = query_obj.get("id", "unknown")
        query = query_obj.get("query", "")
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "natural_language_query": query,
            "include_reasoning": False,
            "validation_errors": []
        }
        
        # Run the pipeline
        result = await self.agent_graph.ainvoke(initial_state)
        
        return {
            "id": query_id,
            "query": query,
            "sql": result.get("generated_sql", ""),
            "row_count": len(result.get("query_results", [])) if result.get("query_results") else 0,
            "success": result.get("execution_error") is None,
            "error": result.get("execution_error") if result.get("execution_error") else None
        }
    
    async def _handle_get_query_history(self, arguments: Dict[str, Any]) -> str:
        """Get query execution history."""
        limit = arguments.get("limit", 10)
        include_results = arguments.get("include_results", False)
        
        # Get recent queries
        recent_queries = self.query_history[-limit:] if limit else self.query_history
        
        # Reverse to show most recent first
        recent_queries = list(reversed(recent_queries))
        
        if not include_results:
            # Remove results to reduce size
            for query in recent_queries:
                query.pop("results", None)
        
        return json.dumps({
            "total_queries": len(self.query_history),
            "returned": len(recent_queries),
            "queries": recent_queries
        }, indent=2)
    
    async def _handle_stream_results(self, arguments: Dict[str, Any]) -> str:
        """Handle streaming of query results."""
        stream_id = arguments.get("stream_id")
        batch_size = arguments.get("batch_size", 100)
        
        if stream_id not in self.active_streams:
            return json.dumps({"error": "Invalid or expired stream ID"})
        
        stream = self.active_streams[stream_id]
        batch = []
        
        try:
            for _ in range(batch_size):
                row = await anext(stream)
                batch.append(row)
        except StopAsyncIteration:
            # End of stream
            del self.active_streams[stream_id]
            return json.dumps({
                "batch": batch,
                "end_of_stream": True
            }, indent=2)
        
        return json.dumps({
            "batch": batch,
            "end_of_stream": False,
            "stream_id": stream_id
        }, indent=2)
    
    async def _handle_estimate_cost(self, arguments: Dict[str, Any]) -> str:
        """Estimate query cost and complexity."""
        query = arguments.get("query", "")
        
        if not query:
            return "Error: No query provided"
        
        cost_estimate = await self._estimate_query_cost(query)
        return json.dumps(cost_estimate, indent=2)
    
    async def _estimate_query_cost(self, query: str) -> Dict[str, Any]:
        """Estimate the cost and complexity of a query."""
        # First, check if it's already SQL or natural language
        is_sql = query.strip().upper().startswith("SELECT")
        
        if not is_sql:
            # Generate SQL first
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "original_query": query,
                "natural_language_query": query,
                "include_reasoning": False,
                "validation_errors": []
            }
            
            # Run only up to SQL generation
            result = await self.agent_graph.ainvoke(initial_state)
            sql_query = result.get("generated_sql", "")
        else:
            sql_query = query
        
        # Estimate query cost
        from .utils.sql_utils import estimate_query_cost
        cost_info = estimate_query_cost(sql_query)
        
        # Add additional info
        cost_info["is_safe"] = validate_sql_syntax(sql_query)[0]
        cost_info["estimated_rows"] = self._estimate_row_count(sql_query)
        
        return cost_info
    
    def _estimate_row_count(self, sql_query: str) -> str:
        """Estimate number of rows the query might return."""
        sql_upper = sql_query.upper()
        
        if "COUNT(*)" in sql_upper:
            return "1 (aggregate)"
        elif "GROUP BY" in sql_upper:
            return "10-1000 (grouped)"
        elif "LIMIT" in sql_upper:
            match = re.search(r"LIMIT\s+(\d+)", sql_upper)
            if match:
                return f"≤{match.group(1)}"
        elif "WHERE" not in sql_upper:
            return "1000+ (no filter)"
        else:
            return "1-1000 (filtered)"
    
    async def _create_result_stream(self, results: List[Any]) -> AsyncIterator:
        """Create an async iterator for streaming results."""
        for row in results:
            yield row
            await asyncio.sleep(0)  # Allow other tasks to run
    
    async def _handle_get_schema(self, arguments: Dict[str, Any]) -> str:
        """Get database schema information."""
        table_names = arguments.get("table_names", [])
        include_sample_data = arguments.get("include_sample_data", False)
        
        try:
            if table_names:
                schema_info = schema_inspector.get_tables_info(table_names)
            else:
                schema_info = schema_inspector.get_all_tables_info()
            
            if include_sample_data:
                for table in schema_info:
                    sample_data = db_toolkit.get_sample_data(table["name"], limit=3)
                    table["sample_data"] = sample_data
            
            return json.dumps(schema_info, indent=2)
        except Exception as e:
            return f"Error getting schema: {str(e)}"
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    """Main entry point."""
    server = EnhancedTextToSQLMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())