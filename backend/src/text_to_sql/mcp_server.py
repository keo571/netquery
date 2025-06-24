"""
MCP (Model Context Protocol) server for Text-to-SQL agent.
Provides text-to-SQL capabilities as an MCP service for the manager agent.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from .agent.graph import text_to_sql_graph
from .config import config
from .create_sample_data import create_infrastructure_database

logger = logging.getLogger(__name__)


class TextToSQLMCPServer:
    """
    MCP Server implementation for Text-to-SQL agent.
    
    Provides the following capabilities:
    - text_to_sql: Convert natural language to SQL and execute
    - schema_analysis: Analyze database schema
    - query_validation: Validate SQL queries
    - database_stats: Get database statistics
    """
    
    def __init__(self):
        self.agent_graph = text_to_sql_graph
        self.server_info = {
            "name": "text_to_sql",
            "version": "1.0.0",
            "description": "Text-to-SQL agent with natural language query processing",
            "capabilities": [
                "text_to_sql",
                "schema_analysis", 
                "query_validation",
                "database_stats"
            ]
        }
        
        # Ensure sample database exists
        self._ensure_sample_database()
    
    def _ensure_sample_database(self):
        """Ensure sample database exists, create if needed."""
        try:
            from .tools.database_toolkit import db_toolkit
            if not db_toolkit.test_connection():
                logger.info("Creating sample database...")
                create_infrastructure_database()
                logger.info("Sample database created successfully")
        except Exception as e:
            logger.error(f"Failed to ensure sample database: {str(e)}")
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities."""
        return {
            "tools": [
                {
                    "name": "text_to_sql",
                    "description": "Convert natural language queries to SQL and execute them",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query to convert to SQL"
                            },
                            "include_reasoning": {
                                "type": "boolean", 
                                "description": "Include explanation of SQL generation process",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "schema_analysis",
                    "description": "Analyze database schema and return table information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific tables to analyze (optional)"
                            },
                            "include_sample_data": {
                                "type": "boolean",
                                "description": "Include sample data in analysis",
                                "default": True
                            }
                        }
                    }
                },
                {
                    "name": "query_validation",
                    "description": "Validate SQL query for safety and correctness",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql_query": {
                                "type": "string",
                                "description": "SQL query to validate"
                            }
                        },
                        "required": ["sql_query"]
                    }
                },
                {
                    "name": "database_stats",
                    "description": "Get database statistics and table information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "detailed": {
                                "type": "boolean",
                                "description": "Include detailed table statistics",
                                "default": False
                            }
                        }
                    }
                }
            ]
        }
    
    async def handle_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool calls."""
        try:
            if tool_name == "text_to_sql":
                return await self._handle_text_to_sql(parameters)
            elif tool_name == "schema_analysis":
                return await self._handle_schema_analysis(parameters)
            elif tool_name == "query_validation":
                return await self._handle_query_validation(parameters)
            elif tool_name == "database_stats":
                return await self._handle_database_stats(parameters)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                    "available_tools": list(self.server_info["capabilities"])
                }
        except Exception as e:
            logger.error(f"Tool call failed for {tool_name}: {str(e)}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool": tool_name
            }
    
    async def _handle_text_to_sql(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text-to-SQL conversion and execution."""
        query = parameters.get("query", "")
        include_reasoning = parameters.get("include_reasoning", True)
        
        if not query:
            return {
                "success": False,
                "error": "No query provided"
            }
        
        logger.info(f"Processing text-to-SQL request: {query[:100]}...")
        
        # Create state for the agent
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "natural_language_query": query,
            "include_reasoning": include_reasoning,
            "validation_errors": []
        }
        
        # Run the agent graph
        result = await self.agent_graph.ainvoke(initial_state)
        
        # Format response
        success = result.get("execution_error") is None
        
        response = {
            "success": success,
            "query": query,
            "response": result.get("formatted_response", "No response generated"),
            "metadata": result.get("response_metadata", {})
        }
        
        if include_reasoning:
            response["reasoning"] = {
                "sql_query": result.get("generated_sql", ""),
                "explanation": result.get("sql_explanation", ""),
                "confidence_score": result.get("confidence_score", 0.0),
                "complexity": result.get("complexity_assessment", "unknown"),
                "tables_used": result.get("relevant_tables", []),
                "execution_time_ms": result.get("execution_time_ms", 0)
            }
        
        if not success:
            response["error"] = result.get("execution_error", "Unknown error")
            response["validation_errors"] = result.get("validation_errors", [])
        
        return response
    
    async def _handle_schema_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle schema analysis requests."""
        table_names = parameters.get("table_names")
        include_sample_data = parameters.get("include_sample_data", True)
        
        try:
            from .tools.schema_inspector import schema_inspector
            
            if table_names:
                # Analyze specific tables
                schema_info = {}
                for table_name in table_names:
                    table_info = schema_inspector.get_table_info(table_name, include_sample_data)
                    if table_info:
                        schema_info[table_name] = {
                            "columns": [
                                {
                                    "name": col.name,
                                    "type": col.type,
                                    "nullable": col.nullable,
                                    "primary_key": col.primary_key,
                                    "default_value": col.default_value
                                }
                                for col in table_info.columns
                            ],
                            "foreign_keys": [
                                {
                                    "column": fk.column,
                                    "referenced_table": fk.referenced_table,
                                    "referenced_column": fk.referenced_column
                                }
                                for fk in table_info.foreign_keys
                            ],
                            "row_count": table_info.row_count,
                            "sample_data": table_info.sample_data if include_sample_data else None
                        }
            else:
                # Analyze all tables
                all_tables = schema_inspector.get_all_tables_info(include_sample_data)
                schema_info = {}
                for table_name, table_info in all_tables.items():
                    schema_info[table_name] = {
                        "columns": [
                            {
                                "name": col.name,
                                "type": col.type,
                                "nullable": col.nullable,
                                "primary_key": col.primary_key
                            }
                            for col in table_info.columns
                        ],
                        "row_count": table_info.row_count,
                        "sample_data": table_info.sample_data[:2] if include_sample_data and table_info.sample_data else None
                    }
            
            # Get relationships
            relationships = schema_inspector.get_table_relationships()
            
            return {
                "success": True,
                "schema": schema_info,
                "relationships": relationships,
                "formatted_schema": schema_inspector.format_schema_for_llm(table_names, include_sample_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Schema analysis failed: {str(e)}"
            }
    
    async def _handle_query_validation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SQL query validation."""
        sql_query = parameters.get("sql_query", "")
        
        if not sql_query:
            return {
                "success": False,
                "error": "No SQL query provided for validation"
            }
        
        try:
            from .tools.safety_validator import safety_validator
            
            validation_result = safety_validator.validate_query(sql_query)
            
            return {
                "success": True,
                "query": sql_query,
                "validation_result": validation_result,
                "is_valid": validation_result["is_valid"],
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"],
                "safety_score": validation_result["safety_score"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Query validation failed: {str(e)}"
            }
    
    async def _handle_database_stats(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database statistics requests."""
        detailed = parameters.get("detailed", False)
        
        try:
            from .tools.database_toolkit import db_toolkit
            
            stats = db_toolkit.get_database_stats()
            
            if detailed:
                # Add more detailed information
                from .tools.schema_inspector import schema_inspector
                all_tables = schema_inspector.get_all_tables_info(include_sample_data=False)
                
                detailed_stats = {}
                for table_name, table_info in all_tables.items():
                    detailed_stats[table_name] = {
                        "row_count": table_info.row_count,
                        "column_count": len(table_info.columns),
                        "has_foreign_keys": len(table_info.foreign_keys) > 0,
                        "primary_key_columns": [col.name for col in table_info.columns if col.primary_key]
                    }
                
                stats["detailed_table_info"] = detailed_stats
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Database stats failed: {str(e)}"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the MCP server."""
        try:
            from .tools.database_toolkit import db_toolkit
            
            db_connected = db_toolkit.test_connection()
            
            health_status = {
                "status": "healthy" if db_connected else "unhealthy",
                "timestamp": self._get_timestamp(),
                "components": {
                    "database": "connected" if db_connected else "disconnected",
                    "agent_graph": "available",
                    "mcp_server": "running"
                },
                "server_info": self.server_info
            }
            
            if not db_connected:
                health_status["issues"] = ["Database connection failed"]
            
            return health_status
            
        except Exception as e:
            return {
                "status": "error",
                "timestamp": self._get_timestamp(),
                "error": str(e)
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# MCP Server Protocol Implementation
class MCPProtocolHandler:
    """Handles MCP protocol communication."""
    
    def __init__(self):
        self.server = TextToSQLMCPServer()
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "tools/list":
                capabilities = await self.server.get_capabilities()
                response = {"tools": capabilities["tools"]}
            
            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_params = params.get("arguments", {})
                response = await self.server.handle_tool_call(tool_name, tool_params)
            
            elif method == "ping":
                response = {"status": "pong"}
            
            elif method == "health":
                response = await self.server.health_check()
            
            else:
                response = {
                    "error": f"Unknown method: {method}",
                    "available_methods": ["tools/list", "tools/call", "ping", "health"]
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": response
            }
            
        except Exception as e:
            logger.error(f"MCP request handling failed: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }


# Simple HTTP server for MCP
async def create_mcp_server(host: str = "localhost", port: int = 8001):
    """Create and run MCP server."""
    from aiohttp import web, web_request
    import aiohttp_cors
    
    handler = MCPProtocolHandler()
    
    async def mcp_endpoint(request: web_request.Request):
        """Handle MCP requests."""
        try:
            data = await request.json()
            response = await handler.handle_request(data)
            return web.json_response(response)
        except Exception as e:
            logger.error(f"MCP endpoint error: {str(e)}")
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }, status=400)
    
    async def health_endpoint(request: web_request.Request):
        """Health check endpoint."""
        health = await handler.server.health_check()
        status_code = 200 if health.get("status") == "healthy" else 503
        return web.json_response(health, status=status_code)
    
    async def capabilities_endpoint(request: web_request.Request):
        """Capabilities endpoint."""
        capabilities = await handler.server.get_capabilities()
        return web.json_response(capabilities)
    
    # Create web application
    app = web.Application()
    
    # Add CORS support
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add routes
    app.router.add_post("/mcp", mcp_endpoint)
    app.router.add_get("/health", health_endpoint)
    app.router.add_get("/capabilities", capabilities_endpoint)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app, host, port


async def run_mcp_server():
    """Run the MCP server."""
    app, host, port = await create_mcp_server()
    
    logger.info(f"Starting Text-to-SQL MCP Server on {host}:{port}")
    logger.info(f"Health check: http://{host}:{port}/health")
    logger.info(f"Capabilities: http://{host}:{port}/capabilities")
    logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
    
    # Run the server
    from aiohttp import web
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the server
    asyncio.run(run_mcp_server())