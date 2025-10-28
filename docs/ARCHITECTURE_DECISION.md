# Architecture Decision Document

## Overview

This document outlines the backend architecture for the Netquery text-to-SQL system, including the FastAPI server, LLM-powered interpretation, and API design.

**Note**: The frontend (React application) is maintained in a separate repository: [netquery-insight-chat](https://github.com/keo571/netquery-insight-chat). This document focuses on the backend API architecture.

## Core Principles

- **Simplicity First**: Direct Python calls, no unnecessary abstraction layers
- **Performance Focused**: Minimize data loading and LLM calls
- **User Controlled**: Interpretation is optional, user-triggered
- **Clear Data Limits**: Well-defined boundaries for preview, interpretation, and export
- **Stateless API**: RESTful design with session management via query IDs

## Architecture Components

### 1. Core Pipeline: Text-to-SQL LangGraph

The main text-to-SQL pipeline (`src/text_to_sql/pipeline/graph.py`):
- 5-stage processing workflow
- **Schema analysis with smart FK expansion** (semantic similarity + relationship traversal)
- SQL generation with direct LLM call (no intermediate planning)
- Safety validation (read-only enforcement)
- Query execution and result formatting
- Automatic visualization detection
- Supports both execution and SQL-only generation modes

**Stage 1 Detail: Schema Analyzer with Smart FK Expansion**

The schema analyzer (`src/text_to_sql/pipeline/nodes/schema_analyzer.py`) uses a two-phase approach to find relevant tables while preventing token explosion:

**Phase 1: Semantic Table Discovery**
- Converts user query to 768-dimensional embedding (Gemini Embeddings)
- Searches pre-cached table description embeddings
- Returns top 5 most relevant tables (threshold: 0.15 similarity)
- Example: "Show customers who ordered recently" → `customers`, `orders`

**Phase 2: Smart FK Expansion** (Speed Optimization)
- **Problem**: Naive FK expansion could explode to 30-40 tables in large databases
- **Solution**: 4-layer optimization strategy

```
Layer 1: HARD LIMITS
  • max_relevant_tables: 5 (semantic matches)
  • max_expanded_tables: 15 (total after FK expansion)
  • max_schema_tokens: 8000 (~25% of LLM context)

Layer 2: SMART PRIORITIZATION
  • Sort semantic tables by relevance score
  • Phase 2a: Add OUTBOUND FKs first (JOIN targets - HIGH priority)
  • Phase 2b: Add INBOUND FKs if space remains (referencing tables - LOWER priority)
  • Stop at 15 tables or token budget

Layer 3: SELECTIVE SAMPLE DATA
  • Semantic matches (5 tables): Full schema + 3 sample rows (~700 tokens each)
  • FK-expanded tables (10 tables): Schema only, NO samples (~400 tokens each)
  • Token savings: ~3,000 tokens (10 tables × 300 tokens)

Layer 4: TOKEN BUDGET TRACKING
  • Real-time estimation: len(schema_text) / 4 ≈ token count
  • Stop adding tables if budget (8,000 tokens) reached
  • Logging: "Schema context: 12 tables, ~6,800 tokens"
```

**Performance Impact:**
- **Small DBs** (10 tables): 5→8 tables, ~4.5k tokens (25% reduction)
- **Medium DBs** (50 tables): 5→15 tables, ~7.5k tokens (42% reduction)
- **Large DBs** (200 tables): 5→15 tables, ~7.5k tokens (75% reduction)
- **Speed improvement**: 2-4x faster LLM processing
- **Cost reduction**: 40-75% lower API costs

### 2. Backend API: FastAPI Server

RESTful API server (`api_server.py`):
- Direct Python imports (no MCP layer)
- Manages query sessions and caching
- Handles all LLM interactions
- Streaming support for large downloads
- Environment-aware (dev/prod modes)

### 3. Database Layer

- **Dev Mode**: SQLite (`data/infrastructure.db`)
  - SSL certificates, network monitoring
  - Detailed health tracking
  - 9 tables with comprehensive metrics

- **Prod Mode**: PostgreSQL (Docker)
  - Wide IP global load balancing
  - Traffic statistics
  - 6 tables with production-like schema

### 4. MCP Server (Optional)

Claude Desktop integration (`src/text_to_sql/mcp_server.py`):
- Exposes text-to-SQL as MCP tool
- Same pipeline as API server
- Tool-based interface for Claude

## API Endpoints

### `/api/generate-sql`

**Purpose**: Generate SQL from natural language without execution

**Input**:
```json
{
  "query": "Show me all unhealthy servers"
}
```

**Process**:
1. Run pipeline with `execute=False`
2. Generate unique query ID
3. Return SQL without execution

**Output**:
```json
{
  "query_id": "abc123",
  "sql": "SELECT * FROM servers WHERE status = 'unhealthy'"
}
```

**Data Handling**: None (no database access)

### `/api/execute/{query_id}`

**Purpose**: Execute generated SQL and return preview data

**Input**: Query ID from `/api/generate-sql`

**Process**:
1. Smart row counting:
   - Fast check if >1000 rows exists
   - Exact count if ≤1000 rows
2. Execute SQL with `LIMIT 50`
3. Cache up to 50 rows in memory
4. Return first 50 rows for preview

**Output**:
```json
{
  "data": [{...}, {...}, ...],  // First 50 rows
  "columns": ["id", "name", "status"],
  "total_count": 156,  // exact count if ≤1000, null if >1000
  "truncated": true  // true if showing 50 of more than 50
}
```

**Data Handling**:
- Fetches: MAX 50 rows
- Returns: MAX 50 rows
- Caches: Up to 50 rows

### `/api/interpret/{query_id}`

**Purpose**: Generate LLM-powered insights and visualization suggestions

**Input**: Query ID

**Process**:
1. Retrieve cached data (no re-execution)
2. Send cached data to LLM (up to 50 rows)
3. Generate textual insights
4. Suggest best visualization (if applicable)

**Output**:
```json
{
  "interpretation": {
    "summary": "Analysis shows 15 unhealthy servers...",
    "key_findings": [
      "80% of unhealthy servers are in us-east-1",
      "Average CPU is 92% for unhealthy servers"
    ]
  },
  "visualization": {
    "type": "bar",
    "title": "Unhealthy Servers by Datacenter",
    "config": {
      "x_column": "datacenter",
      "y_column": "count",
      "reason": "Shows distribution across datacenters"
    }
  },
  "data_truncated": false  // true if >50 total rows
}
```

**Error Handling**:
- LLM failure: Returns error message with data confirmation
- No good visualization: Returns interpretation with `visualization: null`

**Data Handling**:
- **CRITICAL**: Uses ONLY cached data (no re-execution of SQL)
- Analyzes all cached rows (maximum 50 rows)
- Both interpretation AND visualization are limited to these 50 cached rows
- If dataset > 50 rows, analysis is based on a sample

### `/api/download/{query_id}`

**Purpose**: Download complete dataset as CSV

**Input**: Query ID

**Process**:
1. Execute full SQL (no LIMIT)
2. Stream results to CSV
3. Return as downloadable file

**Output**: CSV file (streaming response)

**Data Handling**:
- Fetches: ALL rows
- Memory: Streaming (no full load)

### `/health`

**Purpose**: Health check and system status

**Output**:
```json
{
  "status": "healthy",
  "cache_size": 5,
  "database_connected": true,
  "environment": "dev"
}
```

## Data Flow

```
1. User Question
   ↓
2. POST /api/generate-sql
   → LangGraph pipeline (execute=False)
   → Returns SQL + query_id
   ↓
3. GET /api/execute/{query_id}
   → Execute SQL (LIMIT 50)
   → Cache results
   → Return 50 rows preview
   ↓
4. User Choice:

   A. POST /api/interpret/{query_id}
      → Use cached data ONLY (≤50 rows, NO re-execution)
      → LLM generates insights + viz spec (limited to cached data)
      → Frontend renders visualization (based on ≤50 rows)
      ⚠️ Analysis limited to cached sample if dataset > 50 rows

   B. GET /api/download/{query_id}
      → Execute full SQL (no limit)
      → Stream ALL rows to CSV file
```

## Data Limits Summary

| Operation | Database Fetch | Memory Storage | API Returns | LLM Sees |
|-----------|---------------|----------------|-------------|----------|
| Generate SQL | 0 rows | 0 | SQL query | - |
| Execute/Preview | ≤50 rows | ≤50 rows | 50 rows | - |
| Interpret | 0 (cached) | - | Insights + viz | ≤50 rows |
| Download | ALL rows | 0 (streaming) | CSV file | - |

## Session Management

### Cache Structure

```python
{
    "query_id_abc123": {
        "sql": "SELECT * FROM servers WHERE...",
        "original_query": "Show me unhealthy servers",
        "data": [...],  # up to 50 rows
        "total_count": 5234,  # or None if >1000
        "timestamp": "2025-01-15T10:00:00"
    }
}
```

### Cache Policy

- **Storage Limit**: 50 rows per query
- **TTL**: 10 minutes (configurable via `CACHE_TTL`)
- **Implementation**: In-memory dict for simplicity
- **Future**: Redis for distributed/production deployment
- **Cleanup**: Automatic TTL-based expiration

## Technology Choices

### Why FastAPI (not Flask)?

- ✅ Native async/await support for better performance
- ✅ Built-in OpenAPI documentation (auto-generated)
- ✅ Strong type hints and request validation (Pydantic)
- ✅ Native streaming response support
- ✅ Modern Python features and better performance

### Why Direct Imports (not MCP for API)?

- ✅ Simpler architecture and fewer layers
- ✅ Better performance (no IPC overhead)
- ✅ Easier debugging and error handling
- ✅ MCP only needed for external tool integration (Claude Desktop)
- ✅ More control over request/response handling

### Why In-Memory Cache (not Database)?

- ✅ Faster access for interpretation
- ✅ Avoids re-executing SQL
- ✅ Better user experience (instant response)
- ✅ Reduces database load
- ✅ Simple POC implementation
- ⚠️ Production: Consider Redis for scaling

### Why 50 Row Cache Limit?

- ✅ Optimal for LLM token usage and faster interpretation
- ✅ Fast enough for meaningful analysis
- ✅ Reasonable memory footprint
- ✅ Balance between completeness and performance
- ✅ Transparent to users via `data_truncated` flag
- ⚠️ **IMPORTANT**: Interpretation and visualization can ONLY use these 50 cached rows
- ⚠️ Larger datasets require downloading full CSV for complete analysis

## Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///data/infrastructure.db  # or postgresql://...

# Optional - API Performance
CACHE_TTL=600  # seconds (default: 10 minutes)
MAX_CACHE_ROWS=50  # max rows to cache per query
PREVIEW_ROWS=50  # rows returned in preview
NETQUERY_ENV=dev  # dev or prod

# Optional - Schema Analyzer Speed Optimization
MAX_RELEVANT_TABLES=5   # Semantic search results (default: 5)
MAX_EXPANDED_TABLES=15  # FK expansion cap (default: 15)
MAX_SCHEMA_TOKENS=8000  # Token budget (default: 8000, ~25% of context)
```

**Schema Optimization Parameters:**

These parameters control the smart FK expansion behavior (see Stage 1 details above):

- **`MAX_RELEVANT_TABLES`**: Number of tables returned by semantic search
  - Default: 5
  - Tuning: Increase for complex queries requiring more context
  - Impact: More semantic matches = better coverage but slower

- **`MAX_EXPANDED_TABLES`**: Maximum tables after FK expansion
  - Default: 15 (3x semantic matches)
  - Tuning: Increase for highly normalized databases
  - Impact: More tables = better JOIN discovery but higher token usage

- **`MAX_SCHEMA_TOKENS`**: Token budget for schema context
  - Default: 8000 (~25% of Gemini's 32k context window)
  - Tuning: Decrease for speed, increase for complex schemas
  - Impact: Lower budget = faster responses, fewer tables included

### Environment Profiles

**Dev Mode** (`.env`):
```bash
NETQUERY_ENV=dev
DATABASE_URL=sqlite:///data/infrastructure.db
CANONICAL_SCHEMA_PATH=schema_files/dev_schema.json
```

**Prod Mode** (`.env.prod`):
```bash
NETQUERY_ENV=prod
DATABASE_URL=postgresql://netquery:password@localhost:5432/netquery
CANONICAL_SCHEMA_PATH=schema_files/prod_schema.json
```

## Error Handling

### Large Dataset Scenarios

**Scenario**: Total rows > 50, user requests interpretation

**Behavior**:
- Use cached 50 rows for analysis
- Set `data_truncated: true` in response
- Frontend shows notice about sample-based analysis
- User can download complete data via `/api/download`

**Example**:
```json
{
  "interpretation": {...},
  "visualization": {...},
  "data_truncated": true  // ← Informs frontend
}
```

### Failed SQL Execution

**Scenario**: SQL execution error (syntax, permission, timeout)

**Behavior**:
- Return clear error message
- Log error for debugging
- Don't cache failed queries
- Return 400/500 status code

**Example**:
```json
{
  "error": "Query execution failed: Table 'invalid_table' not found"
}
```

### LLM Interpretation Failure

**Scenario**: LLM service unavailable or returns invalid response

**Behavior**:
- Return user-friendly error message
- Confirm data was retrieved successfully
- Suggest retry or manual analysis

**Example**:
```json
{
  "error": "Interpretation service temporarily unavailable. Your data was retrieved successfully. Please try again or download the results.",
  "data_available": true
}
```

## Security Considerations

### Current (POC/Development)

- CORS configured for localhost development
- SQL injection prevented by existing validator
- Basic error messages (no sensitive data exposure)
- Query safety checks (no DELETE, DROP, etc.)

### Future (Production)

**Authentication & Authorization**:
- JWT-based authentication
- Role-based access control
- Per-user query limits

**Rate Limiting**:
- Per-user request limits
- Per-endpoint rate limiting
- API key management

**Audit & Monitoring**:
- Query logging and audit trail
- Performance monitoring
- Error tracking and alerting
- Sanitized error messages

**Data Security**:
- Encrypted database connections
- Secure credential management
- Data access policies

## Frontend Integration

**Note**: Frontend implementation is in [netquery-insight-chat](https://github.com/keo571/netquery-insight-chat)

### Frontend Responsibilities

1. **Query Input**: Natural language query form
2. **SQL Display**: Show generated SQL with syntax highlighting
3. **Data Preview**: Table display (30 rows)
4. **Interpretation Display**: Show insights and findings
5. **Visualization Rendering**: Render charts from viz specs (Chart.js/Recharts/Plotly)
6. **Download Handling**: CSV file download button
7. **Status Indicators**: Loading states, truncation notices

### Frontend Data Flow

```
User Input
  ↓
Generate SQL → Display SQL
  ↓
Execute → Show 30 row preview + row count
  ↓
User Clicks "Interpret"
  ↓
Show Insights + Render Chart

OR

User Clicks "Download"
  ↓
Download Complete CSV
```

### Visualization Rendering

Frontend receives chart specification and renders using preferred library:

```javascript
// Example with Chart.js
const renderVisualization = (vizSpec, data) => {
  if (!vizSpec) return null;

  const config = {
    type: vizSpec.type,  // 'bar', 'line', 'pie', etc.
    data: {
      labels: data.map(row => row[vizSpec.config.x_column]),
      datasets: [{
        label: vizSpec.title,
        data: data.map(row => row[vizSpec.config.y_column])
      }]
    }
  };

  return new Chart(ctx, config);
};
```

### Data Truncation Handling

Frontend should display notices based on API flags:

```jsx
{truncated && (
  <Notice type="info">
    Showing 30 of {total_count || 'many'} rows
  </Notice>
)}

{data_truncated && (
  <Notice type="info">
    Analysis based on sample data.
    <Button onClick={downloadComplete}>Download Full Data</Button>
  </Notice>
)}
```

## Implementation Status

### Completed ✅

1. Core text-to-SQL pipeline with 5 stages (consolidated SQL generation)
2. FastAPI server with all endpoints
3. In-memory caching system
4. LLM-powered interpretation
5. Smart row counting optimization
6. Streaming CSV download
7. Environment profile system (dev/prod)
8. MCP server integration for Claude Desktop
9. Comprehensive testing framework

### Future Enhancements 🔮

**Phase 1: Production Readiness**
- Redis cache for distributed deployment
- Authentication and authorization
- Rate limiting and quotas
- Enhanced error tracking

**Phase 2: Advanced Features**
- Query cost estimation
- Result set pagination
- Query history and favorites
- Collaborative query sharing

**Phase 3: Intelligence**
- Query recommendation system
- Automatic query optimization
- Adaptive model selection by complexity
- Learning from query patterns

## Benefits of This Architecture

1. **Simple**: No complex orchestration, direct Python calls
2. **Fast**: Cached data, no redundant SQL execution
3. **Scalable**: Clear data limits prevent memory issues
4. **Flexible**: Easy to add features incrementally
5. **User-Friendly**: Quick preview, optional interpretation
6. **Visual**: LLM-suggested visualizations enhance understanding
7. **Testable**: Clear API contracts, comprehensive test suite
8. **Maintainable**: Separation of concerns, good documentation

## What We're NOT Building

Scope clarity to avoid over-engineering:

- ❌ Multi-agent orchestration (not needed yet)
- ❌ Real-time streaming updates (not required)
- ❌ Complex distributed caching (simple in-memory suffices)
- ❌ RAG system for schema understanding (future enhancement)
- ❌ Automatic query refinement loop (future enhancement)
- ❌ Multi-tenancy (POC is single-tenant)

## Success Criteria

- ✅ Generate SQL from natural language (80%+ success rate)
- ✅ Preview loads in <2 seconds
- ✅ Interpretation available for all datasets
- ✅ Visualizations suggested and renderable
- ✅ Full data download for any size
- ✅ No duplicate SQL execution
- ✅ Clear feedback on data limits
- ✅ Comprehensive test coverage
- ✅ Works in both dev and prod modes

## Related Documentation

- [Getting Started](GETTING_STARTED.md) - Setup and usage guide
- [Evaluation](EVALUATION.md) - Testing and evaluation framework
- [Schema Ingestion](SCHEMA_INGESTION.md) - Schema management
- [Sample Queries](SAMPLE_QUERIES.md) - Example queries for testing
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

---

**Last Updated**: 2025-01-15
