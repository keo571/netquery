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
   - `semantic_table_finder.py` - Enhanced semantic table relevance scoring
   - `safety_validator.py` - Query safety checks

3. **Utils** (`src/text_to_sql/utils/`)
   - `chart_generator.py` - SVG chart generation (line, bar, pie, scatter)
   - `html_exporter.py` - HTML report generation with embedded charts
   - `llm_utils.py` - LLM configuration and utilities
   - `sql_utils.py` - SQL parsing and validation utilities

4. **MCP Server** (`src/text_to_sql/`)
   - `mcp_server.py` - Standard MCP implementation

5. **Scripts & CLI**
   - `scripts/create_sample_data.py` - Pure SQL sample data generator 
   - `scripts/evaluate_queries.py` - Comprehensive query evaluation framework
   - `scripts/evaluate_mcp.py` - MCP tool selection testing
   - `scripts/export_database_tables.py` - Database export utility
   - `gemini_cli.py` - Enhanced CLI with chart and export support

6. **Output Structure**
   - `outputs/query_data/` - CSV exports from text-to-SQL queries
   - `outputs/query_reports/` - HTML reports from text-to-SQL queries
   - `testing/table_exports/` - Database table exports for analysis
   - `testing/evaluations/` - Evaluation reports and testing artifacts

## Recent Improvements

### 1. Database & Code Simplification (Latest)
- ✅ Refactored create_sample_data.py to use pure raw SQL (eliminated SQLAlchemy complexity)
- ✅ Fixed SQLite path resolution to use data/ folder consistently
- ✅ Fixed datetime/float type conversion errors in sample data generation
- ✅ Reorganized SAMPLE_QUERIES.md for better clarity and removed redundancies
- ✅ Streamlined README.md documentation

### 2. Chart Generation & Visualization System
- ✅ Added automatic chart type detection (line, bar, pie, scatter)
- ✅ Implemented static SVG chart generation (no JavaScript dependencies)
- ✅ Created dedicated chart_generator.py module
- ✅ Smart data pattern recognition for appropriate visualizations
- ✅ HTML report generation with embedded charts

### 3. Enhanced Semantic Understanding  
- ✅ Fixed schema analysis error handling for robust pipeline
- ✅ Optimized similarity threshold from 0.3 to 0.15 for better table discovery
- ✅ Enhanced table descriptions with domain-specific context
- ✅ Added key metrics highlighting for infrastructure terminology
- ✅ Improved column name mapping for network infrastructure

### 4. Code Organization & Output Structure
- ✅ Refactored interpreter module (reduced from 700+ to 184 lines)
- ✅ Extracted SQL utilities to `utils/sql_utils.py`
- ✅ Organized prompts in `prompts/` directory
- ✅ Added config management with hot-reloading
- ✅ Created modular utilities (chart_generator.py, html_exporter.py, llm_utils.py)
- ✅ Organized output structure: `outputs/` for user results, `dev/` for development artifacts

### 5. Evaluation & Testing Framework
- ✅ Built comprehensive evaluation system (evaluate_queries.py)
- ✅ Added batch testing across all query categories  
- ✅ Pipeline stage tracking (schema, SQL, execution, charts)
- ✅ HTML evaluation reports with detailed metrics
- ✅ Database export utilities (export_database_tables.py)

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

# Optional: Override default database location  
DATABASE_URL=sqlite:///data/infrastructure.db
```

## Quick Commands

```bash
# Development
python scripts/create_sample_data.py          # Create sample data (REQUIRED for CLI/Python API)
python gemini_cli.py "your query"             # Test queries via CLI
python -m src.text_to_sql.mcp_server          # Start MCP server (auto-creates data if missing)

# Testing with Charts & Exports
python gemini_cli.py "Show me all load balancers"
python gemini_cli.py "Show network traffic over time" --html
python gemini_cli.py "Display server performance by datacenter" --csv --explain

# Testing & Evaluation
python scripts/evaluate_mcp.py               # Test MCP tool selection
python scripts/evaluate_queries.py          # Run comprehensive pipeline evaluation
python scripts/export_database_tables.py    # Export all database tables
```

## Adding or Updating Table Descriptions

When adding new tables or updating existing ones:

1. **Edit the descriptions file**: `src/text_to_sql/table_descriptions.yaml`
   ```yaml
   your_new_table: "Description focusing on key metrics and use cases"
   ```

2. **Clear the embeddings cache** to rebuild with new descriptions:
   ```bash
   rm -rf .embeddings_cache/
   ```

3. **Test** that your table is being found correctly:
   ```bash
   python gemini_cli.py "query about your new table"
   ```

The semantic table finder uses these descriptions to match user queries to relevant tables, so make descriptions clear and include key terms users might search for.

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

4. **Chart Generation & Export**
   - `src/text_to_sql/utils/chart_generator.py` - SVG chart generation system
   - `src/text_to_sql/utils/html_exporter.py` - HTML report generation
   - `evaluate_queries.py` - Comprehensive evaluation framework
   - `export_database_tables.py` - Database export utilities

5. **MCP Integration**
   - `src/text_to_sql/mcp_server.py` - Standard MCP server

## Development Workflow

1. **Making Changes**
   ```bash
   # 1. Create feature branch
   git checkout -b feature/your-feature
   
   # 2. Make changes
   # 3. Test locally
   python gemini_cli.py "test query"
   
   # 4. Test MCP server
   python -m src.text_to_sql.mcp_server
   ```

2. **Adding Features**
   - Update relevant node in `pipeline/nodes/`
   - Add new utilities in `utils/` if needed
   - Update this documentation
   - Test with sample queries
   - Run evaluation suite to verify improvements

3. **Debugging**
   - Use debug mode: `LOG_LEVEL=DEBUG python gemini_cli.py "query"`
   - Test individual components with Python imports
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

*Last Updated: December 2025*
*Version: 1.1.0 - Enhanced Semantic Understanding & Visualization System*