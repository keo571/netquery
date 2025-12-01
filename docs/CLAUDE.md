# CLAUDE.md - AI Assistant Context

This document provides essential context for AI assistants working on the Netquery Text-to-SQL pipeline.

## Project Overview

**Netquery** is a network infrastructure Text-to-SQL system that converts natural language queries into SQL for infrastructure monitoring. It's specifically designed for network engineers and operators who need to query complex infrastructure databases without SQL expertise.

## Core Architecture

```
User Query → Triage → Schema Analysis → SQL Generation → Validation → Execution → Result Interpretation
```

### Key Components

1. **Pipeline** (`src/text_to_sql/pipeline/`)
   - LangGraph-based orchestration
   - **Six processing nodes** working in sequence
   - State management across the pipeline
   - **Nodes**: triage.py, schema_analyzer.py, sql_generator.py, validator.py, executor.py, interpreter.py
   - **Helper functions** in `state.py`: `create_success_step()`, `create_warning_step()`, `create_error_step()`

2. **Database** (`src/text_to_sql/database/`)
   - Database connection management
   - `engine.py` - Database engine configuration

3. **Tools** (`src/text_to_sql/tools/`)
   - `database_toolkit.py` - Database operations with lazy loading
   - `semantic_table_finder.py` - Enhanced semantic table relevance scoring with embedding cache
   - `safety_validator.py` - Query safety checks

3a. **Stores** (`src/text_to_sql/stores/`)
   - `embedding_store.py` - Embedding cache storage (local files or pgvector)
   - `LocalFileEmbeddingStore` - File-based cache for development
   - `PgVectorEmbeddingStore` - PostgreSQL pgvector for production
   - See [SIMPLE_GUIDE.md](SIMPLE_GUIDE.md) for usage

4. **Utils** (`src/text_to_sql/utils/`)
   - `chart_generator.py` - SVG chart generation (line, bar, pie, scatter)
   - `html_exporter.py` - HTML report generation with embedded charts
   - `llm_utils.py` - LLM configuration and utilities
   - `sql_utils.py` - SQL parsing and validation utilities

5. **Prompts** (`src/text_to_sql/prompts/`)
   - `result_interpretation.py` - Result interpretation prompts
   - `sql_generation.py` - SQL generation prompts
   - `_shared.py` - Shared prompt utilities (database-specific instructions)

6. **Common** (`src/common/`)
   - `constants.py` - **CENTRALIZED** data limits and chart configurations (single source of truth)
   - `config.py` - Configuration management with hot-reloading
   - `schema_summary.py` - Schema overview utilities
   - **Always import from `constants.py`** - never hardcode limits!

7. **Configuration**
   - `mcp_server.py` - Standard MCP implementation

8. **Scripts & CLI**
   - `scripts/create_data_sqlite.py` - Pure SQL sample data generator
   - `testing/evaluate_queries.py` - Comprehensive query evaluation framework

9. **API Layer** (`src/api/`)
   - `server.py` - FastAPI server with four main endpoints
   - `interpretation_service.py` - LLM-powered result interpretation

10. **Output Structure**
   - `data/` - Database files (infrastructure.db)
   - `outputs/query_data/` - CSV exports from text-to-SQL queries
   - `outputs/query_reports/` - HTML reports from text-to-SQL queries
   - `testing/table_exports/` - Database table exports for analysis
   - `testing/evaluations/` - Evaluation reports and testing artifacts

## API Architecture

The system now includes a FastAPI server providing a clean separation between SQL generation, execution, and interpretation:

### API Endpoints

1. **`POST /api/generate-sql`**
   - Converts natural language to SQL without execution
   - Returns `query_id` for subsequent operations
   - Uses existing LangGraph pipeline with `execute=False`

2. **`GET /api/execute/{query_id}`**
   - Executes SQL and caches up to MAX_CACHE_ROWS rows
   - Returns first PREVIEW_ROWS rows for preview
   - Smart counting: exact count ≤1000 rows, "unknown" for larger datasets
   - Optimized for performance with fast >1000 row detection

3. **`POST /api/interpret/{query_id}`**
   - LLM-powered analysis of cached results
   - Returns interpretation summary and key findings
   - Suggests single best visualization (or null if inappropriate)
   - Graceful error handling with user-friendly messages

4. **`GET /api/download/{query_id}`**
   - Streams complete dataset as CSV
   - No row limits, handles large datasets efficiently

### Cache Strategy

- **Size**: Up to MAX_CACHE_ROWS rows per query (optimized for faster LLM analysis)
- **TTL**: 10 minutes default
- **Counting**: Fast check for >1000 rows vs exact count ≤1000
- **Memory**: In-memory dict for POC (Redis for production)

### Error Handling Philosophy

- **LLM interpretation fails**: Return user-friendly message "Analysis temporarily unavailable. Your data was retrieved successfully."
- **Visualization parsing fails**: Return interpretation with `visualization: null`
- **No data**: Simple "No data found" message
- **Principle**: If LLM can't handle it, don't over-engineer fallbacks

## Recent Improvements

### 1. Simplified Schema Workflow (October 2025)
- ✅ Created simple `./schema` wrapper command (no more complexity!)
- ✅ Unified workflow: just `build` and `query` for all databases
- ✅ Automatic schema file naming and embedding cache management
- ✅ Smart embedding cache with namespace isolation
- ✅ Automatic cache checking before rebuilding embeddings
- ✅ Support for both local file cache and PostgreSQL pgvector
- ✅ Reduced subsequent query time from ~2s to ~0.3s (6.7x faster!)
- ✅ See [SIMPLE_GUIDE.md](SIMPLE_GUIDE.md) for usage

### 2. PostgreSQL Production Support (September 2025)
- ✅ Database-agnostic SQL prompts (auto-detects SQLite vs PostgreSQL)
- ✅ PostgreSQL driver (psycopg2-binary) and system dependencies in Docker
- ✅ Enhanced safety config with PostgreSQL system table blocking
- ✅ Environment switching seamlessly works with PostgreSQL URLs
- ✅ Production-ready with connection pooling and proper syntax

### 2. FastAPI Server & Interpretation Service (September 2025)
- ✅ Built FastAPI server with four optimized endpoints
- ✅ Implemented smart row counting (≤1000 vs >1000) for performance
- ✅ Reduced cache size to MAX_CACHE_ROWS rows (LLM-optimized for speed, configurable in constants.py)
- ✅ Simplified interpretation service: single visualization vs multiple
- ✅ Removed over-engineered fallbacks: LLM-first approach
- ✅ Graceful error handling with user-friendly messages
- ✅ Separated interpretation success from visualization parsing

### 2. Documentation & Structure Improvements (September 2025)
- ✅ Updated project structure documentation in README.md and CLAUDE.md
- ✅ Refined node descriptions for accuracy (validator.py now correctly describes safety-only validation)
- ✅ Cleaned up import statements in pipeline nodes
- ✅ Removed references to non-existent scripts
- ✅ Improved project structure clarity with proper directory hierarchy

### 2. Database & Code Simplification
- ✅ Refactored scripts/create_data_sqlite.py to use pure raw SQL (eliminated SQLAlchemy complexity)
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

### 7. Excel Schema Integration with Human-in-the-Loop (October 2025)
- ✅ Full Excel schema ingestion support for databases without introspectable schemas
- ✅ Two-sheet format: table_schema (tables/columns) and mapping (relationships)
- ✅ **Schema Ingestion**: Excel files can be converted to canonical JSON format for enhanced descriptions
- ✅ **Embedding integration**: Canonical schema descriptions are embedded for semantic table discovery
- ✅ **Two-tier description priority**: Canonical schema (human/LLM) > Auto-generated from database
- ✅ Automatic column type inference from naming patterns (fallback)
- ✅ Enhanced table descriptions with relationship context
- ✅ CLI support: `--schema` parameter for canonical schema JSON
- ✅ Seamless merge with live database reflection
- ✅ Cached analyzer instances with schema hash for performance
- ✅ Schema building tool: `python -m src.schema_ingestion build` to create canonical schemas from Excel or database

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
**Solution**: Use semantic similarity scoring for better table relevance matching. Consider using Excel schema to provide richer descriptions.

### Issue: Database without foreign key constraints
**Solution**: Use Excel schema to define relationships between tables. The system will use this metadata to enhance SQL generation.

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

# Database Configuration
DATABASE_URL=sqlite:///data/infrastructure.db  # Query target database (default)
# For client queries: DATABASE_URL=postgresql://client-host/client-db

# Embedding Cache Configuration (Optional)
EMBEDDING_DATABASE_URL=postgresql://localhost/your-embedding-db  # Use pgvector for embeddings
# If not set, uses local file cache (.embeddings_cache/)

# Model Configuration (Optional)
EMBEDDING_MODEL=gemini-embedding-001         # Gemini embedding model (default)
EMBEDDING_CACHE_DIR=.embeddings_cache        # Local cache directory (default)
```

## Quick Commands

```bash
# Schema Management (RECOMMENDED - Simple!)
./schema build <database-url>                 # Build schema from any database (once)
./schema query <database-url> "your query"    # Query with automatic schema loading
./schema list                                 # List all schemas
./schema info <database-url>                  # Show schema details

# See SIMPLE_GUIDE.md for complete usage

# Development (Alternative - Advanced)
python scripts/create_data_sqlite.py          # Create sample data (REQUIRED for CLI/API)
python gemini_cli.py "your query"             # Test queries via CLI
python -m src.text_to_sql.mcp_server          # Start MCP server (auto-creates data if missing)

# FastAPI Server (NEW)
python -m uvicorn src.api.server:app --reload --port 8000   # Start API server
python test_api.py                            # Test all endpoints
python test_llm_interpretation.py             # Test LLM interpretation specifically
python test_large_query.py                    # Test with large datasets

# Testing with Charts & Exports
python gemini_cli.py "Show me all load balancers"
python gemini_cli.py "Show network traffic over time" --html
python gemini_cli.py "Display server performance by datacenter" --csv --explain

# Testing with Canonical Schema
python gemini_cli.py "Show all users" --schema schema_files/custom_schema.json
python gemini_cli.py "Display orders by customer" --schema schema_files/custom_schema.json --html

# Building Canonical Schema
python -m src.schema_ingestion build --database-url sqlite:///data/mydb.db --output schema_files/my_sqlite_schema.json
python -m src.schema_ingestion build --database-url postgresql://user:pass@host/db --output schema_files/my_postgres_schema.json

# Testing & Evaluation
python testing/evaluate_queries.py          # Run comprehensive pipeline evaluation
python testing/export_database_tables.py    # Export all database tables
python test_excel_integration.py            # Test Excel schema integration
```

## Adding or Updating Table Descriptions

The system supports **two approaches**:

### Approach 1: Database Reflection (Well-Named Tables Only)

Works automatically for databases with meaningful names:
- Table names like: `customers`, `orders`, `products`
- Column names like: `customer_id`, `email`, `order_total`

**Limitations**:
- ❌ Fails with cryptic names (`tbl_001`, `data_x`, `col_a`)
- ❌ No semantic context for table discovery
- ⚠️ Not recommended unless your database has excellent naming conventions

### Approach 2: Excel Schema with Human Descriptions (Recommended)

**For databases with cryptic names**, use the interactive schema builder:

```bash
# Step 1: Build schema JSON
python -m src.schema_ingestion build --database-url sqlite:///data/mydb.db --output schema_files/my_schema.json

# The script will:
# - Show each table with sample data
# - Prompt you for table/column descriptions
# - Auto-detect relationships
# - Generate canonical schema JSON (edit or convert to Excel as needed)

# Step 2: Review and edit the generated Excel file if needed

# Step 3: Convert to canonical format
python -m src.schema_ingestion build \
  --excel schema_output.xlsx \
  --output schema_files/my_schema.json

# Step 4: Use with queries
python gemini_cli.py "your query" --schema schema_files/my_schema.json
```

**Benefits**:
- ✅ Human-in-the-loop for both database introspection AND schema creation
- ✅ Works with ANY database, regardless of naming
- ✅ Canonical format ensures consistency
- ✅ Descriptions are embedded for semantic table discovery
- ✅ One-time effort, reusable forever

**See documentation**:
- [Interactive Schema Builder Guide](docs/SCHEMA_BUILDER_GUIDE.md)
- [Excel Schema Format](docs/EXCEL_SCHEMA_FORMAT.md)

## Key Files to Understand

1. **Pipeline Core**
   - `src/text_to_sql/pipeline/graph.py` - Main LangGraph orchestration and node connections
   - `src/text_to_sql/pipeline/state.py` - State management and data structures across pipeline

2. **Processing Nodes** (Five-stage pipeline)
   - `src/text_to_sql/pipeline/nodes/schema_analyzer.py` - Schema discovery and table selection using semantic similarity
   - `src/text_to_sql/pipeline/nodes/sql_generator.py` - Direct LLM-based SQL generation from natural language
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
   - `testing/evaluate_queries.py` - Comprehensive evaluation framework
   - `scripts/create_data_sqlite.py` - Sample data generation
   - `testing/export_database_tables.py` - Database export utilities

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
- **Model**: Uses Google Gemini 1.5 Flash for direct SQL generation from natural language

## Remember

1. **This is a network infrastructure system** - optimize for network operations queries
2. **Safety is paramount** - never allow destructive operations
3. **Performance matters** - use streaming and caching
4. **Simplicity wins** - prefer SQLAlchemy over complex manual mapping
5. **Test everything** - especially SQL generation and validation

---

*Last Updated: September 2025*
*Version: 1.3.0 - Updated Documentation & Project Structure*
