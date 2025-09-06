# CLAUDE.md - AI Assistant Context

This document provides essential context for AI assistants working on the Netquery Text-to-SQL pipeline.

## Project Overview

**Netquery** is a network infrastructure Text-to-SQL system that converts natural language queries into SQL for infrastructure monitoring. It's specifically designed for network engineers and operators who need to query complex infrastructure databases without SQL expertise.

## Core Architecture

```
User Query → Schema Analysis → Query Planning → SQL Generation → Validation → Execution → Result Interpretation
```

### Key Components

1. **Pipeline** (`src/text_to_sql/pipeline/`)
   - LangGraph-based orchestration
   - Six processing nodes working in sequence
   - State management across the pipeline

2. **Tools** (`src/text_to_sql/tools/`)
   - `database_toolkit.py` - Database operations with lazy loading
   - `semantic_table_finder.py` - Semantic table relevance scoring
   - `safety_validator.py` - Query safety checks

3. **MCP Server** (`src/text_to_sql/`)
   - `mcp_server.py` - Standard MCP implementation

## Recent Improvements

### 1. Config & Database Management (Latest)
- ✅ Fixed SQLite path resolution with absolute paths for reliability
- ✅ Added lazy loading to database connections for better initialization
- ✅ Simplified MCP server response formatting
- ✅ Made result interpretation more technical and direct

### 2. Code Organization
- ✅ Extracted SQL utilities to `utils/sql_utils.py`
- ✅ Organized prompts in `prompts/` directory
- ✅ Added config management with hot-reloading

### 3. Docker Support
- ✅ Multi-stage Dockerfile for optimized builds
- ✅ docker-compose.yml with PostgreSQL & Redis options
- ✅ Makefile for easy management

### 4. Schema Intelligence
- ✅ Removed penalty for large tables (was incorrectly penalizing important data)
- ✅ Improved semantic scoring for network infrastructure domain
- ✅ Enhanced semantic table finder for better relevance matching

## Domain Focus: Network Infrastructure

The system is optimized for network infrastructure queries:

### Key Entities
- **Load Balancers** - F5, HAProxy, Nginx
- **Backend Servers** - Pool members, real servers
- **VIPs** - Virtual IPs, virtual services
- **Data Centers** - Sites, regions, zones
- **SSL Certificates** - TLS, cert management
- **Metrics** - Performance, monitoring data

### Common Query Patterns
```sql
-- Status queries
"Show me all load balancers that are down"
"Which backend servers are unhealthy?"

-- Performance queries  
"What's the average response time by datacenter?"
"Show bandwidth utilization trends"

-- Security queries
"Which SSL certificates expire soon?"
"List all VIPs without valid certificates"

-- Capacity queries
"What's the current load on each datacenter?"
"Show server utilization above 80%"
```

## Important Design Decisions

### 1. Large Table Handling
**DON'T** penalize large tables - they often contain the most important data (orders, metrics, logs).
**DO** flag them for optimization and add appropriate LIMIT clauses.

### 2. Schema Discovery
**USE** semantic similarity-based table finding for better relevance matching.
**WHY**: Semantic analysis understands context better than simple keyword matching.

### 3. Safety First
**ALWAYS** validate queries before execution:
- Block destructive operations (DELETE, DROP, UPDATE)
- Enforce row limits
- Validate against safety rules

### 4. Performance
**USE** streaming for large result sets.
**IMPLEMENT** query cost estimation before execution.
**CACHE** schema information when possible.

## Code Style Guidelines

### Python
- Use type hints for all functions
- Docstrings for all public methods
- Dataclasses for data structures
- Async/await for I/O operations

### SQL Generation
- Always use parameterized queries
- Include LIMIT clauses
- Use explicit JOINs over implicit
- Add comments for complex queries

### Error Handling
- Log errors with context
- Provide user-friendly error messages
- Implement graceful degradation
- Never expose sensitive information

## Testing Approach

### Unit Tests (TODO)
```python
# Test individual components
test_sql_cleaning()
test_query_optimization()
test_schema_reflection()
```

### Integration Tests
```python
# Test full pipeline
test_text_to_sql_pipeline()
test_mcp_server_endpoints()
```

### Performance Tests
```python
# Test with large datasets
test_streaming_performance()
test_batch_processing()
```

## Common Issues & Solutions

### Issue: Schema finder selecting wrong tables
**Solution**: Use semantic similarity scoring for better table relevance matching

### Issue: Large tables getting penalized
**Solution**: Already fixed - large tables now get optimization flags instead of penalties

### Issue: Complex queries failing
**Solution**: Implement query simplification and retry logic

### Issue: Slow performance on large results
**Solution**: Use streaming and pagination

## Future Improvements

### High Priority
1. **Add Redis caching** for frequently used queries
2. **Implement query history** learning
3. **Add unit tests** for all components
4. **Create query explain mode** for debugging

### Medium Priority
1. **Multi-database support** (currently SQLite-focused)
2. **Query optimization hints** based on execution plans
3. **Prometheus metrics** integration
4. **GraphQL API** option

### Nice to Have
1. **Natural language explanations** of SQL queries
2. **Query suggestions** based on schema
3. **Visual query builder** integration
4. **Automated index recommendations**

## Environment Variables

```bash
# Required
GEMINI_API_KEY=your_key_here

# Database
DATABASE_URL=sqlite:///infrastructure.db  # or postgresql://...

# Optional
LOG_LEVEL=INFO
MAX_RESULT_ROWS=1000
ENABLE_CACHE=true
```

## Quick Commands

```bash
# Development
make dev          # Start dev environment
make test         # Run tests
make format       # Format code

# Docker
make build        # Build images
make up           # Start services
make logs         # View logs

# Database
make db-create    # Create sample data
make db-shell     # Access database

# MCP
make mcp-test     # Test MCP server
```

## Key Files to Understand

1. **Pipeline Core**
   - `src/text_to_sql/pipeline/graph.py` - Main orchestration
   - `src/text_to_sql/pipeline/state.py` - State management

2. **SQL Generation**
   - `src/text_to_sql/pipeline/nodes/sql_generator.py` - LLM-based generation
   - `src/text_to_sql/utils/sql_utils.py` - SQL utilities

3. **Schema Analysis**
   - `src/text_to_sql/tools/semantic_table_finder.py` - Semantic table relevance scoring
   - `src/text_to_sql/tools/database_toolkit.py` - Database operations and schema reflection

4. **MCP Integration**
   - `src/text_to_sql/mcp_server.py` - Standard MCP server

## Development Workflow

1. **Making Changes**
   ```bash
   # 1. Create feature branch
   git checkout -b feature/your-feature
   
   # 2. Make changes
   # 3. Test locally
   make test
   
   # 4. Format code
   make format
   
   # 5. Test in Docker
   make rebuild
   ```

2. **Adding Features**
   - Update relevant node in `pipeline/nodes/`
   - Add tests in `tests/`
   - Update this documentation
   - Test with sample queries

3. **Debugging**
   - Check logs: `make logs`
   - Use debug mode: `LOG_LEVEL=DEBUG`
   - Test individual components
   - Use SQLAlchemy echo mode for SQL debugging

## Network Infrastructure Specifics

### Table Naming Conventions
- Plural names: `load_balancers`, `backend_servers`
- Relationship tables: `lb_backend_mappings`
- Metrics tables: `monitoring_metrics`, `performance_stats`

### Common Relationships
```sql
load_balancers -> vip_pools -> backend_servers
datacenters -> network_zones -> servers
ssl_certificates -> vips -> services
```

### Performance Considerations
- Metrics tables are typically large (millions of rows)
- Use time-based partitioning where possible
- Index on commonly queried columns (timestamp, status)
- Aggregate old data into summary tables

## Contact & Resources

- **Documentation**: See README.md, DOCKER_GUIDE.md
- **Architecture**: See TEXT_TO_SQL_ARCHITECTURE.md
- **Issues**: GitHub Issues
- **Model**: Uses Google Gemini for SQL generation

## Remember

1. **This is a network infrastructure system** - optimize for network operations queries
2. **Safety is paramount** - never allow destructive operations
3. **Performance matters** - use streaming and caching
4. **Simplicity wins** - prefer SQLAlchemy over complex manual mapping
5. **Test everything** - especially SQL generation and validation

---

*Last Updated: September 2025*
*Version: 1.1.0*