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
   - **Nodes**: executor.py, interpreter.py, query_planner.py, schema_analyzer.py, sql_generator.py, validator.py

2. **Database** (`src/text_to_sql/database/`)
   - Database connection management
   - `engine.py` - Database engine configuration

3. **Tools** (`src/text_to_sql/tools/`)
   - `database_toolkit.py` - Database operations with lazy loading
   - `semantic_table_finder.py` - Enhanced semantic table relevance scoring
   - `safety_validator.py` - Query safety checks

4. **Utils** (`src/text_to_sql/utils/`)
   - `chart_generator.py` - SVG chart generation (line, bar, pie, scatter)
   - `html_exporter.py` - HTML report generation with embedded charts
   - `llm_utils.py` - LLM configuration and utilities
   - `sql_utils.py` - SQL parsing and validation utilities

5. **Prompts** (`src/text_to_sql/prompts/`)
   - `query_planning.py` - Query planning prompts
   - `result_interpretation.py` - Result interpretation prompts
   - `sql_generation.py` - SQL generation prompts
   - `_shared.py` - Shared prompt utilities

6. **Configuration**
   - `config.py` - Configuration management with hot-reloading
   - `mcp_server.py` - Standard MCP implementation

7. **Scripts & CLI**
   - `scripts/create_sample_data.py` - Pure SQL sample data generator
   - `scripts/evaluate_queries.py` - Comprehensive query evaluation framework
   - `scripts/export_database_tables.py` - Database export utility
   - `gemini_cli.py` - Enhanced CLI with chart and export support

8. **Output Structure**
   - `data/` - Database files (infrastructure.db)
   - `outputs/query_data/` - CSV exports from text-to-SQL queries
   - `outputs/query_reports/` - HTML reports from text-to-SQL queries
   - `testing/table_exports/` - Database table exports for analysis
   - `testing/evaluations/` - Evaluation reports and testing artifacts

## Recent Improvements

### 1. Documentation & Structure Improvements (Latest - September 2025)
- ✅ Updated project structure documentation in README.md and CLAUDE.md
- ✅ Refined node descriptions for accuracy (validator.py now correctly describes safety-only validation)
- ✅ Cleaned up import statements in pipeline nodes
- ✅ Removed references to non-existent scripts
- ✅ Improved project structure clarity with proper directory hierarchy

### 2. Database & Code Simplification
- ✅ Refactored create_sample_data.py to use pure raw SQL (eliminated SQLAlchemy complexity)
- ✅ Fixed SQLite path resolution to use data/ folder consistently
- ✅ Fixed datetime/float type conversion errors in sample data generation
- ✅ Reorganized SAMPLE_QUERIES.md for better clarity and removed redundancies
- ✅ Streamlined README.md documentation

### 3. Chart Generation & Visualization System
- ✅ Added automatic chart type detection (line, bar, pie, scatter)
- ✅ Implemented static SVG chart generation (no JavaScript dependencies)
- ✅ Created dedicated chart_generator.py module
- ✅ Smart data pattern recognition for appropriate visualizations
- ✅ HTML report generation with embedded charts

### 4. Enhanced Semantic Understanding
- ✅ Fixed schema analysis error handling for robust pipeline
- ✅ Optimized similarity threshold from 0.3 to 0.15 for better table discovery
- ✅ Enhanced table descriptions with domain-specific context
- ✅ Added key metrics highlighting for infrastructure terminology
- ✅ Improved column name mapping for network infrastructure

### 5. Code Organization & Output Structure
- ✅ Refactored interpreter module (reduced from 700+ to 184 lines)
- ✅ Extracted SQL utilities to `utils/sql_utils.py`
- ✅ Organized prompts in `prompts/` directory
- ✅ Added config management with hot-reloading
- ✅ Created modular utilities (chart_generator.py, html_exporter.py, llm_utils.py)
- ✅ Organized output structure: `outputs/` for user results, `testing/` for development artifacts
- ✅ Added dedicated `database/` module for connection management

### 6. Evaluation & Testing Framework
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
1. **Add unit tests** for all pipeline components and utilities
2. **Improve error handling** with more specific error types and recovery strategies
3. **Add query caching** for frequently used queries (Redis or local cache)
4. **Enhanced logging** with structured logging and better debugging information

### Medium Priority
1. **Multi-database support** - PostgreSQL, MySQL, SQL Server adapters
2. **Query optimization hints** based on execution plans and performance analysis
3. **Streaming results** for very large datasets with pagination
4. **Natural language explanations** of generated SQL queries for transparency

### Nice to Have
1. **Query suggestions** based on schema analysis and common patterns
2. **Visual query builder** integration for complex query construction
3. **Automated index recommendations** based on query patterns
4. **Real-time monitoring** integration with Prometheus/Grafana
5. **GraphQL API** as an alternative interface to MCP

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
python scripts/evaluate_queries.py          # Run comprehensive pipeline evaluation
python scripts/export_database_tables.py    # Export all database tables
```

## Adding or Updating Table Descriptions

The system uses dynamic table descriptions generated from schema reflection rather than a static YAML file. Table descriptions are automatically created based on:

1. **Table names and column names** - Used for semantic similarity matching
2. **Column types and constraints** - Analyzed to understand data patterns
3. **Sample data** - Used to infer content and relationships

To improve table discovery for new tables:

1. **Use descriptive table and column names** that match domain terminology
2. **Add meaningful sample data** that represents real use cases
3. **Clear embeddings cache** after schema changes:
   ```bash
   rm -rf .embeddings_cache/
   ```

3. **Test table discovery**:
   ```bash
   python gemini_cli.py "query about your new table"
   ```

## Key Files to Understand

1. **Pipeline Core**
   - `src/text_to_sql/pipeline/graph.py` - Main LangGraph orchestration and node connections
   - `src/text_to_sql/pipeline/state.py` - State management and data structures across pipeline

2. **Processing Nodes** (Six-stage pipeline)
   - `src/text_to_sql/pipeline/nodes/schema_analyzer.py` - Schema discovery and table selection
   - `src/text_to_sql/pipeline/nodes/query_planner.py` - JSON query plan generation
   - `src/text_to_sql/pipeline/nodes/sql_generator.py` - LLM-based SQL generation
   - `src/text_to_sql/pipeline/nodes/validator.py` - Safety and security validation
   - `src/text_to_sql/pipeline/nodes/executor.py` - Database query execution
   - `src/text_to_sql/pipeline/nodes/interpreter.py` - Result formatting and chart generation

3. **Database Layer**
   - `src/text_to_sql/database/engine.py` - Database connection and configuration
   - `src/text_to_sql/tools/database_toolkit.py` - Database operations and schema reflection

4. **Intelligence Layer**
   - `src/text_to_sql/tools/semantic_table_finder.py` - Semantic table relevance scoring with embeddings
   - `src/text_to_sql/tools/safety_validator.py` - Query safety validation rules
   - `src/text_to_sql/prompts/` - LLM prompts for each pipeline stage

5. **Utilities & Export**
   - `src/text_to_sql/utils/chart_generator.py` - SVG chart generation (line, bar, pie, scatter)
   - `src/text_to_sql/utils/html_exporter.py` - HTML report generation with embedded charts
   - `src/text_to_sql/utils/llm_utils.py` - LLM configuration and API management
   - `src/text_to_sql/utils/sql_utils.py` - SQL parsing and validation utilities

6. **CLI & Testing**
   - `gemini_cli.py` - Command-line interface with export options
   - `scripts/evaluate_queries.py` - Comprehensive evaluation framework
   - `scripts/create_sample_data.py` - Sample data generation
   - `scripts/export_database_tables.py` - Database export utilities

7. **MCP Integration**
   - `src/text_to_sql/mcp_server.py` - Model Context Protocol server implementation

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

- **Documentation**: See README.md and docs/SAMPLE_QUERIES.md
- **Issues**: GitHub Issues at https://github.com/keo571/netquery
- **Model**: Uses Google Gemini 1.5 Flash for SQL generation and query planning

## Remember

1. **This is a network infrastructure system** - optimize for network operations queries
2. **Safety is paramount** - never allow destructive operations
3. **Performance matters** - use streaming and caching
4. **Simplicity wins** - prefer SQLAlchemy over complex manual mapping
5. **Test everything** - especially SQL generation and validation

---

*Last Updated: September 2025*
*Version: 1.3.0 - Updated Documentation & Project Structure*