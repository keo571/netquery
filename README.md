# Netquery - Network Infrastructure Text-to-SQL

An AI-powered assistant that converts natural language queries into SQL for network infrastructure monitoring and management. Designed specifically for network engineers and operators who need to query complex infrastructure databases without SQL expertise.

## Overview

Netquery helps network operations teams query their infrastructure databases using natural language:

- **"Show me all load balancers that are unhealthy"**
- **"Which SSL certificates expire in the next 30 days?"** 
- **"What's the average CPU utilization by datacenter?"**
- **"List all VIP addresses in production environment"**

## Key Features

- **🌐 Network Infrastructure Focus**: Optimized for load balancers, servers, VIPs, SSL certificates, and monitoring data
- **🤖 Natural Language Queries**: Convert plain English to SQL automatically  
- **🔒 Safety First**: Query validation prevents destructive operations
- **🚀 MCP Server**: Integrates with Claude Desktop and other AI assistants
- **📊 Smart Schema Analysis**: Automatically understands database relationships
- **⚡ Performance Optimized**: Handles large infrastructure databases efficiently

## Network Infrastructure Entities

Netquery understands common network infrastructure components:

- **Load Balancers** - F5, HAProxy, Nginx configurations
- **Backend Servers** - Pool members, real servers, health status
- **Virtual IPs (VIPs)** - Virtual services, IP addresses
- **Data Centers** - Sites, regions, availability zones  
- **SSL Certificates** - TLS certificates, expiration tracking
- **Monitoring Metrics** - Performance data, utilization statistics

## Quick Start

### Prerequisites
- Python 3.8+
- Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd netquery
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

4. **Create sample data** (Required first step):
   ```bash
   python -m src.text_to_sql.create_sample_data
   ```
   
   This creates `infrastructure.db` with realistic network infrastructure data including load balancers, servers, SSL certificates, VIP pools, and backend mappings.

### Usage Examples

**Direct Python Usage:**
```python
from src.text_to_sql.pipeline.graph import text_to_sql_graph
from langchain_core.messages import HumanMessage

# Query your infrastructure
result = await text_to_sql_graph.ainvoke({
    "messages": [HumanMessage(content="Show me all unhealthy load balancers")],
    "original_query": "Show me all unhealthy load balancers"
})
```

**CLI Testing:**
```bash
# Simple CLI for testing (requires sample data)
python gemini_cli.py "Show me all load balancers"
python gemini_cli.py "Which SSL certificates expire soon?"
```

**MCP Server (for Claude Desktop):**
```bash
# Start the MCP server (requires sample data)
python -m src.text_to_sql.mcp_server
```

## Common Query Patterns

### Status Monitoring
```
"Show me all load balancers that are down"
"Which backend servers are unhealthy?" 
"List servers in maintenance mode"
```

### Performance Analysis
```
"What's the average response time by datacenter?"
"Show bandwidth utilization trends"
"Which servers have CPU usage above 80%?"
```

### Security & Compliance
```
"Which SSL certificates expire in the next 90 days?"
"List all VIPs without valid certificates"
"Show load balancers with weak SSL configurations"
```

### Capacity Planning
```
"What's the current load distribution across datacenters?"
"Show server utilization by region"
"Which load balancers are approaching capacity limits?"
```

## Project Structure

```
src/text_to_sql/
├── pipeline/           # LangGraph-based processing pipeline
│   ├── graph.py       # Main orchestration
│   ├── state.py       # State management
│   └── nodes/         # Processing nodes
├── tools/             # Database and analysis tools
│   ├── database_toolkit.py    # Database operations
│   ├── safety_validator.py    # Query safety checks
│   └── semantic_table_finder.py # Schema analysis
├── prompts/           # LLM prompts for each stage
├── utils/             # SQL utilities and helpers
├── database/          # Database connection management
├── create_sample_data.py      # Network infrastructure sample data
└── mcp_server.py             # MCP server implementation
```

## Configuration

Key environment variables:

```bash
# Required
GEMINI_API_KEY=your_api_key_here

# Optional  
DATABASE_URL=sqlite:///infrastructure.db
LOG_LEVEL=INFO
MAX_RESULT_ROWS=1000
LLM_MODEL=gemini-2.5-flash
```

## Architecture

```
Natural Language Query 
    ↓
Schema Analysis (identify relevant tables)
    ↓  
Query Planning (understand intent)
    ↓
SQL Generation (create safe SQL)
    ↓
Safety Validation (prevent destructive operations)
    ↓
Query Execution (run against database)
    ↓
Result Interpretation (format for humans)
```

## Safety Features

- **Query Validation**: Blocks DELETE, DROP, UPDATE, and other destructive operations
- **Row Limits**: Automatically adds LIMIT clauses to prevent large result sets
- **Schema Validation**: Ensures queries only access valid tables and columns
- **Error Handling**: Graceful failure with informative error messages

## Development

### Testing

**Prerequisites**: Always create sample data first:
```bash
# Create sample infrastructure database
python -m src.text_to_sql.create_sample_data
```

**Test with CLI:**
```bash
# Try different complexity queries
python gemini_cli.py "Show me all load balancers"
python gemini_cli.py "Which servers have high CPU usage?"
python gemini_cli.py "What's the average memory usage by datacenter?"
```

**Test with MCP:**
```bash
# Start MCP server
python -m src.text_to_sql.mcp_server
```

See `SAMPLE_QUERIES.md` for comprehensive test cases organized by complexity level.

### Adding New Infrastructure Types

1. Update sample data patterns in `create_sample_data.py`
2. Add domain knowledge to prompts in `prompts/`
3. Update schema analysis in `tools/semantic_table_finder.py`

## Contributing

1. Follow the coding standards in `CLAUDE.md`
2. Focus on network infrastructure use cases
3. Ensure safety validation for all new query types
4. Add appropriate logging and error handling

## License

[Your License Here]

## Support

For network infrastructure-specific questions or feature requests, please open an issue describing your use case and the types of queries you need to support.