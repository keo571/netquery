# MCP Implementation Guide

## Overview

This repository now includes a **standard Model Context Protocol (MCP)** implementation that exposes the Text-to-SQL functionality as an MCP server. This allows any MCP-compatible client (like Claude Desktop) to query your infrastructure database using natural language.

## Architecture

### Previous Architecture (Custom)
```
Manager Agent --> Custom "MCP-like" HTTP API --> Text-to-SQL Agent
```

### New Architecture (Standard MCP)
```
Any MCP Client (Claude, etc.) --> MCP Server --> Text-to-SQL Pipeline
                                        |
                                        └── Single tool encapsulating:
                                            ├── Schema Analysis
                                            ├── Query Planning
                                            ├── SQL Generation
                                            ├── Safety Validation
                                            ├── Query Execution
                                            └── Result Formatting
```

## Project Structure (After Cleanup)

```
netbot-v1/
├── src/text_to_sql/                 # Core text-to-sql engine
│   ├── pipeline/                    # LangGraph text-to-SQL pipeline
│   │   ├── graph.py                 # Main pipeline orchestration
│   │   ├── state.py                 # Pipeline state management
│   │   └── nodes/                   # Processing nodes
│   ├── tools/                       # Database tools (toolkit, validator, inspector)
│   ├── mcp_server_standard.py       # ✅ Standard MCP server
│   ├── mcp_client_example.py        # ✅ Example client
│   └── create_sample_data.py        # Database setup
├── tests/                           # Test files for text-to-SQL pipeline  
├── .env                             # Environment variables
├── langgraph.json                   # LangGraph configuration
├── claude_desktop_config.json       # Claude Desktop config
├── MCP_IMPLEMENTATION.md            # This file
└── requirements.txt                 # Updated with MCP SDK
```

**Removed/Cleaned:**
- ❌ `backend/` - Unnecessary directory nesting 
- ❌ `backend/src/manager/` - Manager agent (unnecessary routing)
- ❌ `backend/src/rag/` - RAG placeholder (not implemented)  
- ❌ `frontend/` - Web interface (MCP-only focus)
- ❌ `run.py` - Flask API server (simplified to MCP-only)
- ❌ `mcp_server_legacy.py` - Legacy custom MCP implementation
- ❌ Python cache files (`__pycache__/`, `*.pyc`)
- ❌ Manager-related tests and configurations
- ✅ **Renamed:** `agent/` → `pipeline/` (better terminology)
- ✅ **Flattened:** `backend/src/` → `src/` (cleaner structure)

## Features

### Tools
The MCP server exposes two main tools:

1. **text_to_sql** - Convert natural language to SQL and execute
   - Handles the entire pipeline internally
   - Returns formatted results with optional explanations
   - Includes safety validation and error handling

2. **get_schema** - Retrieve database schema information
   - Get all tables or specific ones
   - Optional sample data inclusion
   - Formatted for readability

### Resources
The server provides two resources:

1. **schema://infrastructure** - Complete database schema
2. **schema://relationships** - Table relationships and foreign keys

## Installation

1. Install the MCP Python SDK (already done):
```bash
./venv/bin/pip install mcp
```

2. Ensure environment variables are set in `.env`:
```bash
GEMINI_API_KEY=your_api_key_here
```

## Usage

### Running the MCP Server Standalone

```bash
cd src/text_to_sql
python mcp_server_standard.py
```

### Testing with the Example Client

```bash
cd src/text_to_sql
python mcp_client_example.py
```

### Running Tests

```bash
cd tests
python test_text_to_sql_direct.py
```

### Integrating with Claude Desktop

1. Copy the configuration to Claude Desktop's config directory:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Update the configuration with your actual paths and API key:
```json
{
  "mcpServers": {
    "netbot-text-to-sql": {
      "command": "python",
      "args": [
        "/path/to/netbot-v1/src/text_to_sql/mcp_server_standard.py"
      ],
      "env": {
        "PYTHONPATH": "/path/to/netbot-v1",
        "GEMINI_API_KEY": "your_actual_api_key"
      }
    }
  }
}
```

3. Restart Claude Desktop

4. In Claude, you can now query your infrastructure database:
   - "Show me all load balancers"
   - "Which SSL certificates expire soon?"
   - "What's the average CPU usage by datacenter?"

## Example Queries

Once connected, you can ask questions like:

**Infrastructure Monitoring:**
- "Show me the status of all load balancers"
- "Check VIP health across all data centers"
- "Which SSL certificates are expiring soon?"
- "What's the geographic distribution of our web traffic?"

**Performance Analysis:**
- "Show load balancer capacity analysis"
- "Which backend servers have the highest response times?"
- "Give me a summary of VIP performance"
- "What's the health status of our global traffic management?"

**Network Configuration:**
- "List all VIPs in the DMZ zone"
- "Show network interfaces for lb-prod-1"
- "What's the current routing configuration?"
- "Display SSL certificate bindings"

## How It Works

1. **Query Reception**: The MCP server receives a natural language query through the `text_to_sql` tool

2. **Pipeline Execution**: The server runs the complete Text-to-SQL pipeline:
   - Analyzes database schema
   - Plans the query approach
   - Generates SQL using Gemini LLM
   - Validates query safety
   - Executes against the database
   - Formats results for readability

3. **Response**: Returns formatted results with optional SQL explanation

## Benefits of This Implementation

1. **Standard Protocol**: Uses official MCP specification, not a custom variant
2. **Tool Discovery**: Clients can discover available tools dynamically
3. **Encapsulation**: Complex pipeline hidden behind simple tool interface
4. **Compatibility**: Works with any MCP-compatible client
5. **Extensibility**: Easy to add new tools or resources

## Comparison with Previous Implementation

| Aspect | Old (Custom) | New (Standard MCP) |
|--------|--------------|-------------------|
| Protocol | HTTP/REST with JSON-RPC-like format | Standard MCP over stdio |
| Transport | HTTP on port 8001 | stdio (stdin/stdout) |
| Client Support | Custom clients only | Any MCP client |
| Tool Discovery | Custom endpoint | Standard MCP discovery |
| Resources | Not supported | Full resource support |
| Sessions | Custom session management | MCP session handling |

## Extending the Server

To add new tools:

1. Add tool definition in `list_tools()` handler
2. Implement tool logic in `call_tool()` handler
3. Update this documentation

Example:
```python
@self.server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        # ... existing tools ...
        Tool(
            name="analyze_performance",
            description="Analyze database performance metrics",
            inputSchema={...}
        )
    ]
```

## Troubleshooting

1. **Import errors**: Ensure PYTHONPATH includes the project root
2. **Database not found**: Run `python create_sample_data.py` to create sample database
3. **API key issues**: Check GEMINI_API_KEY in environment variables
4. **Connection issues**: Verify the server script path in configuration

## Learning from This Implementation

This implementation demonstrates:

1. **Proper MCP server structure** using the official SDK
2. **Tool and resource definitions** following MCP specification
3. **stdio transport** for process communication
4. **Encapsulation pattern** for complex pipelines
5. **Error handling** in MCP context

Study `mcp_server_standard.py` to understand:
- How to initialize an MCP server
- How to register handlers for tools and resources
- How to handle tool calls with proper typing
- How to format responses for MCP clients

## Next Steps

Potential improvements:
1. Add more tools (query history, optimization suggestions)
2. Implement prompts for common query patterns
3. Add sampling capabilities for large result sets
4. Create additional resources (query templates, best practices)
5. Add authentication/authorization layer