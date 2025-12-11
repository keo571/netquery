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

The main text-to-SQL pipeline (`src/text_to_sql/pipeline/graph.py`) is a 7-stage LangGraph workflow:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Text-to-SQL Pipeline                         │
└─────────────────────────────────────────────────────────────────┘

User Query: "which servers are unhealthy?"
    ↓
┌───────────────────────┐
│ Stage 0: Triage       │  Fast heuristics to filter non-DB questions
│ ~1ms                  │  Rejects: "What is a server?" → Helpful message
└───────────────────────┘
    ↓ (database query)
┌───────────────────────┐
│ Stage 1: Cache Lookup │  Two-tier caching with conversational support
│ ~10ms (hit)           │  • Extract: "which are unhealthy?"
│ ~2-2.7s (miss)        │  • Check cache (embedding + SQL)
└───────────────────────┘  • Rewrite if follow-up: "Show unhealthy servers"
    ↓
    ├─ FULL HIT? → Skip to Stage 4 (Validator) ✅ ~10ms
    ├─ PARTIAL HIT? → Continue to Stage 2 with cached embedding
    └─ MISS? → Continue to Stage 2, generate new embedding
    ↓
┌───────────────────────┐
│ Stage 2: Schema       │  Semantic table discovery + Smart FK expansion
│ Analyzer              │  • Embed query (or use cached)
│ ~500ms                │  • Find top 5 relevant tables (similarity search)
└───────────────────────┘  • Expand with FKs (max 15 tables, token budget)
    ↓
┌───────────────────────┐
│ Stage 3: SQL          │  LLM generates SQL from natural language
│ Generator             │  • Uses selected schema context
│ ~1.5-2s               │  • Direct LLM call (no intermediate planning)
└───────────────────────┘  • Cache result for future queries
    ↓
┌───────────────────────┐
│ Stage 4: Validator    │  Safety validation
│ ~10ms                 │  • Read-only enforcement (no DELETE, DROP, etc.)
└───────────────────────┘  • SQL syntax validation
    ↓
┌───────────────────────┐
│ Stage 5: Executor     │  Execute SQL and fetch results
│ ~50-500ms             │  • Run query with LIMIT MAX_CACHE_ROWS
└───────────────────────┘  • Cache results in memory
    ↓
┌───────────────────────┐
│ Stage 6: Interpreter  │  Optional LLM-powered interpretation
│ (optional)            │  • User-triggered analysis
│ ~1-2s                 │  • Uses cached results (no re-execution)
└───────────────────────┘  • Auto-detect visualizations

Total Time:
  • Full cache HIT: ~10ms (skip stages 2-3)
  • Partial cache HIT: ~2s (skip embedding generation)
  • Cache MISS: ~2.5-2.7s (full pipeline)
```

**Key Features**:
- **Performance-first**: 70-80% cache hit rate after warmup
- **Conversational**: Handles follow-up questions with query extraction & rewriting
- **Safe**: Read-only validation prevents destructive operations
- **Smart**: Automatic FK expansion with token budget management
- **Flexible**: Supports both SQL-only and full execution modes

**Stage 0: Query Triage**

The triage node (`src/text_to_sql/pipeline/nodes/triage.py`) uses fast heuristics to filter out non-database questions:

**Purpose**: Avoid expensive pipeline processing for obvious non-queries

**Detection Patterns**:
- Definition requests: "What is a load balancer?", "Define SSL"
- Explanation questions: "How does DNS work?", "Why does BGP exist?"
- General knowledge: "Who invented SQL?", "Tell me about networking"

**Benefits**:
- ⚡ **Speed**: ~1ms response (vs 2-3 seconds for full pipeline)
- 💰 **Cost savings**: No LLM/embedding API calls for non-queries
- ✅ **Better UX**: Helpful message with schema suggestions vs confusing SQL error

**Smart Exceptions**:
- "How many servers are unhealthy?" → Allowed (query indicator)
- "What are the top 10 servers?" → Allowed (superlative modifier)
- "Show me what SSL certificates are expiring" → Allowed (data retrieval)

**Output**: If rejected, returns helpful message with schema overview for suggestions

**Stage 1: Cache Lookup** (Performance Optimization with Conversational Query Support)

The cache lookup node (`src/text_to_sql/pipeline/nodes/cache_lookup.py`) implements intelligent caching with special handling for conversational follow-up questions.

**Purpose**: Maximize performance while supporting natural conversations

**Architecture: Three-Path Routing**

The cache lookup follows a clean three-path design:

```python
def cache_lookup_node(state):
    extracted_query = extract_current_query(full_query)  # Step 1
    cached_result = query_cache.get(extracted_query)     # Step 2

    if cached_result and has_sql:
        return _handle_full_cache_hit(...)      # Path 1: Fastest
    elif cached_result:
        return _handle_partial_cache_hit(...)   # Path 2: May rewrite
    else:
        return _handle_cache_miss(...)          # Path 3: May rewrite
```

**Path 1: FULL Cache HIT** (~10ms)
- Have both embedding AND SQL cached
- Skip entire pipeline (schema analysis + SQL generation)
- No query rewriting needed
- Route directly to validator
- Example: "Show load balancers" → Return cached SQL immediately

**Path 2: PARTIAL Cache HIT** (~2s or ~2.2s)
- Have embedding but NO SQL
- Check if follow-up question (ambiguous without context)
- **If standalone**: Use cached embedding, skip rewriting (~2s)
- **If follow-up**: Rewrite query, generate new embedding (~2.2s)
- Example: "which are unhealthy?" after "Show servers" → Rewrite to "Show unhealthy servers"

**Path 3: Cache MISS** (~2.5s or ~2.7s)
- No cached data
- Check if follow-up question
- **If standalone**: Generate from scratch (~2.5s)
- **If follow-up**: Rewrite first, then generate (~2.7s)
- Cache results for future queries

**Conversational Query Handling**:

Problem: Frontend sends conversation context that breaks cache matching:
```
"CONVERSATION HISTORY...\nUSER'S NEW QUESTION: which are unhealthy?"
```

Solution: Two-phase approach
1. **Query Extraction** - Extract current query for cache matching
2. **Smart Rewriting** - Rewrite ambiguous follow-ups only when needed

```
User: "Show me all servers"
  → Cache MISS → Generate SQL → Cache it

User: "which ones are unhealthy?"
  ↓
Extract: "which are unhealthy?"
  ↓
Check cache: FULL HIT? → Return cached SQL (no rewriting!) ✅ Fast
           MISS/PARTIAL? → Rewrite to "Show unhealthy servers" → Continue ✅ Accurate
```

**Key Optimization**: Lazy rewriting
- Full cache HIT → Skip rewriting (already have SQL)
- Partial HIT/MISS → Rewrite if ambiguous (need accurate table selection)

**Performance Impact**:
- **Full cache hit**: ~10ms (no rewriting, skip pipeline)
- **Partial cache hit (standalone)**: ~2s (use cached embedding)
- **Partial cache hit (follow-up)**: ~2.2s (rewrite ~200ms + new embedding)
- **Cache miss (standalone)**: ~2.5s (normal pipeline)
- **Cache miss (follow-up)**: ~2.7s (rewrite ~200ms + pipeline)
- **Expected hit rate**: 70-80% after warmup (with conversational support)

**Cache Invalidation on User Feedback**:

When users click thumbs down on generated SQL:
```python
# In frontend chat adapter
invalidate_query_cache(user_question)  # Smart invalidation

# What happens:
# 1. Keeps embedding (table selection was probably correct)
# 2. Clears SQL only (logic was wrong)
# 3. Next retry generates fresh SQL but reuses embedding (~2s vs ~2.5s)
```

**Benefits**:
- Faster retry after thumbs down (~2s vs ~2.5s if we cleared everything)
- Table selection usually correct, SQL logic needs rework
- Graceful degradation (embedding still useful)

**Implementation Details**:
- Storage: SQLite (`query_cache.db`)
- Normalization: lowercase, remove action verbs, whitespace
- Fuzzy matching: SequenceMatcher (85% similarity threshold)
- Query extraction: Regex patterns for conversation context
- Query rewriting: LLM-based (only when needed)
- Invalidation: UPDATE SQL=NULL (keep embedding) vs DELETE (nuclear option)

**Why This Design?**:
1. **Fast for common case**: Full hits skip rewriting (~10ms)
2. **Accurate for follow-ups**: Rewriting only when doing table selection
3. **Simple to understand**: Three clear paths, each in own function
4. **Maintainable**: Helper functions separate concerns
5. **Production-ready**: Same performance as complex version, easier to debug

---

### Detailed Cache Implementation

The cache system consists of several key components working together:

#### 1. Query Extraction (`src/text_to_sql/utils/query_extraction.py`)

Extracts the current question from conversation context sent by the frontend.

**Patterns Detected**:
- `USER'S NEW QUESTION: {query}` (primary pattern from BFF)
- `Current: {query}` (alternative)
- `Question: {query}` (alternative)
- Last `User:` message in multi-line format

**Example**:
```python
extract_current_query("""
CONVERSATION HISTORY:
  User asked: Show me all servers
USER'S NEW QUESTION: which are unhealthy?
""")
# Returns: "which are unhealthy?"
```

#### 2. Query Rewriter (`src/text_to_sql/utils/query_rewriter.py`)

Converts ambiguous follow-ups to standalone queries for accurate table selection.

**Detection**: Identifies follow-ups by checking for:
- Conversation history markers
- Ambiguous pronouns: "which", "those", "them", "it"
- Continuation words: "more", "other", "also"
- Missing subject questions

**Rewriting Strategy**:
```python
# Prompt to LLM:
"""
Previous question: Show me all servers
Follow-up question: which are unhealthy?

Rewrite the follow-up to be self-contained and standalone.
"""
# LLM output: "Show me all unhealthy servers"
```

**Conditional Rewriting**:
```python
def rewrite_if_needed(full_query, extracted_query, cache_hit_type):
    # Skip if we have SQL already
    if cache_hit_type == 'full':
        return extracted_query

    # Skip if not a follow-up
    if not needs_rewriting(full_query, extracted_query):
        return extracted_query

    # Rewrite for accurate table selection
    return rewrite_follow_up_query(full_query, extracted_query)
```

#### 3. Cache Storage (`src/text_to_sql/tools/query_embedding_cache.py`)

**Storage**: SQLite database (`.embeddings_cache/query_cache.db`)

**Schema**:
```sql
CREATE TABLE query_cache (
    id INTEGER PRIMARY KEY,
    original_query TEXT,
    normalized_query TEXT,
    embedding BLOB,
    generated_sql TEXT,
    hit_count INTEGER,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP
)
```

**Normalization**: Lowercase, remove action verbs, whitespace normalization

**Fuzzy Matching**: SequenceMatcher with 85% similarity threshold for near-matches

**Invalidation Methods**:
- `invalidate(query)` - Sets SQL to NULL, keeps embedding (smart invalidation)
- `clear_all()` - Nuclear option, removes all entries

#### 4. Cache Utilities (`src/text_to_sql/utils/cache_utils.py`)

Provides external access to cache management:

```python
from src.text_to_sql.utils.cache_utils import invalidate_query_cache

# Invalidate after thumbs down
invalidated = invalidate_query_cache(user_question)

# Get cache statistics
stats = get_cache_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"Total hits: {stats['total_hits']}")
```

#### Frontend Integration for Cache Invalidation

When users click thumbs down, the frontend chat adapter should invalidate the cache:

```python
# In chat_adapter.py (netquery-insight-chat repo)

from src.text_to_sql.utils.cache_utils import invalidate_query_cache

@app.post("/api/feedback")
async def submit_feedback_endpoint(request: FeedbackRequest):
    # ... existing code ...

    # On thumbs down, invalidate cache
    if request.type == "thumbs_down" and request.user_question:
        try:
            invalidated = invalidate_query_cache(request.user_question)
            if invalidated:
                logger.info(f"Cache invalidated for negative feedback")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")

    return {"status": "ok"}
```

**User Flow After Thumbs Down**:
1. User asks "Show unhealthy servers"
2. System returns SQL: `SELECT * FROM servers WHERE status = 'down'`
3. User unhappy, clicks 👎
4. Cache invalidated for this query (SQL removed, embedding kept)
5. User clicks "Try Again" → Generates fresh SQL (may use different approach)
6. Next retry: ~2s (PARTIAL HIT - reuses embedding) vs ~2.5s (full MISS)

#### Cache Logging and Monitoring

| Operation | Log Level | What's Logged |
|-----------|-----------|---------------|
| **Cache Initialization** | INFO | Cache path, fuzzy settings |
| **Full Cache HIT** | INFO | Query, time saved (2-3s) |
| **Partial Cache HIT** | INFO | Query, time saved (500ms) |
| **Cache MISS** | DEBUG | Query |
| **Cache Storage** | INFO | Query, normalized, SQL status |
| **SQL Invalidation** | INFO | Query, affected entries |
| **Query Extraction** | INFO | Full vs extracted query length |

**Monitoring Commands**:
```bash
# Cache hit rate
grep "cache HIT" application.log | wc -l
grep "Cache MISS" application.log | wc -l

# User dissatisfaction (thumbs down)
grep "Invalidated SQL" application.log | wc -l

# Query extraction (conversational queries)
grep "Extracted current query" application.log | wc -l
```

**Example Log Flow (Thumbs Down → Retry)**:
```
# First query (cache miss)
INFO: Cached generated SQL for query: 'Show unhealthy servers'

# User unhappy, clicks thumbs down
INFO: ✅ Invalidated SQL (kept embedding) for query: 'Show unhealthy servers'
   Retry performance: ~2s (fast)

# User retries same question
INFO: ⚡ PARTIAL cache HIT for query: 'Show unhealthy servers'
   Have embedding, will skip embedding API call (~500ms saved)

# User happy this time, asks same question later
INFO: 🚀 FULL cache HIT for query: 'Show unhealthy servers'
   Skipping schema analysis and SQL generation (saving ~2-3 seconds)
```

#### Cache Performance Summary

| Path | Cache State | Rewrite? | Embedding | Time | Typical Frequency |
|------|-------------|----------|-----------|------|-------------------|
| **Full Hit** | Have SQL | NO | Not used | ~10ms | High (after warmup) |
| **Partial Hit (standalone)** | Have embedding | NO | Use cached | ~2s | Medium |
| **Partial Hit (follow-up)** | Have embedding | YES | Generate new | ~2.2s | Low |
| **Miss (standalone)** | Empty | NO | Generate new | ~2.5s | Medium |
| **Miss (follow-up)** | Empty | YES | Generate new | ~2.7s | Low |

**Most common path**: Full Hit (~10ms) - This is why the optimization matters!

#### Example Conversational Session

```
User: "Show me all servers"
→ Cache MISS
→ No rewriting (standalone)
→ Embed: "show me all servers"
→ Tables: [servers]
→ SQL: SELECT * FROM servers
→ Time: 2.5s

User: "which ones are unhealthy?"
→ Extract: "which are unhealthy?"
→ Cache check: MISS
→ Rewrite: "Show me all unhealthy servers"
→ Embed: "show me all unhealthy servers"
→ Tables: [servers] ✅ CORRECT
→ SQL: SELECT * FROM servers WHERE status = 'unhealthy'
→ Cache with: "which are unhealthy?"
→ Time: 2.7s (2.5s + 200ms rewrite)

User: "which ones are unhealthy?" (asks again later)
→ Extract: "which are unhealthy?"
→ Cache check: FULL HIT ✅
→ No rewriting needed
→ Return cached SQL
→ Time: 10ms ✅ FAST

User: "which are offline?"
→ Extract: "which are offline?"
→ Cache check: MISS
→ Rewrite: "Show me all offline servers"
→ Embed: "show me all offline servers"
→ Tables: [servers] ✅ CORRECT
→ Time: 2.7s
```

---

**Stage 2 Detail: Schema Analyzer with Smart FK Expansion**

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
- Multi-database support via `SCHEMA_ID` configuration

### 3. Database Layer

- **Sample Database**: SQLite (`data/sample.db`)
  - Load balancers, backends, virtual IPs
  - Network performance metrics
  - Sample data for demonstration

- **Neila Database**: SQLite (`data/neila.db`)
  - Customer-specific schema
  - Production-like data structure

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
2. Execute SQL with `LIMIT MAX_CACHE_ROWS`
3. Cache up to MAX_CACHE_ROWS rows in memory
4. Return first PREVIEW_ROWS rows for preview

**Output**:
```json
{
  "data": [{...}, {...}, ...],  // First PREVIEW_ROWS rows
  "columns": ["id", "name", "status"],
  "total_count": 156,  // exact count if ≤1000, null if >1000
  "truncated": true  // true if showing PREVIEW_ROWS of more than PREVIEW_ROWS
}
```

**Data Handling**:
- Fetches: MAX MAX_CACHE_ROWS rows
- Returns: MAX PREVIEW_ROWS rows
- Caches: Up to MAX_CACHE_ROWS rows

### `/api/interpret/{query_id}`

**Purpose**: Generate LLM-powered insights and visualization suggestions

**Input**: Query ID

**Process**:
1. Retrieve cached data (no re-execution)
2. Send cached data to LLM (up to MAX_CACHE_ROWS rows)
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
  "data_truncated": false  // true if >MAX_CACHE_ROWS total rows
}
```

**Error Handling**:
- LLM failure: Returns error message with data confirmation
- No good visualization: Returns interpretation with `visualization: null`

**Data Handling**:
- **CRITICAL**: Uses ONLY cached data (no re-execution of SQL)
- Analyzes all cached rows (maximum MAX_CACHE_ROWS rows)
- Both interpretation AND visualization are limited to these MAX_CACHE_ROWS cached rows
- If dataset > MAX_CACHE_ROWS rows, analysis is based on a sample

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
   → Execute SQL (LIMIT MAX_CACHE_ROWS)
   → Cache results
   → Return PREVIEW_ROWS rows preview
   ↓
4. User Choice:

   A. POST /api/interpret/{query_id}
      → Use cached data ONLY (≤MAX_CACHE_ROWS rows, NO re-execution)
      → LLM generates insights + viz spec (limited to cached data)
      → Frontend renders visualization (based on ≤MAX_CACHE_ROWS rows)
      ⚠️ Analysis limited to cached sample if dataset > MAX_CACHE_ROWS rows

   B. GET /api/download/{query_id}
      → Execute full SQL (no limit)
      → Stream ALL rows to CSV file
```

## Data Limits Summary

| Operation | Database Fetch | Memory Storage | API Returns | LLM Sees |
|-----------|---------------|----------------|-------------|----------|
| Generate SQL | 0 rows | 0 | SQL query | - |
| Execute/Preview | ≤MAX_CACHE_ROWS rows | ≤MAX_CACHE_ROWS rows | PREVIEW_ROWS rows | - |
| Interpret | 0 (cached) | - | Insights + viz | ≤MAX_CACHE_ROWS rows |
| Download | ALL rows | 0 (streaming) | CSV file | - |

## Session Management

### Cache Structure

```python
{
    "query_id_abc123": {
        "sql": "SELECT * FROM servers WHERE...",
        "original_query": "Show me unhealthy servers",
        "data": [...],  # up to MAX_CACHE_ROWS rows
        "total_count": 5234,  # or None if >1000
        "timestamp": "2025-01-15T10:00:00"
    }
}
```

### Cache Policy

- **Storage Limit**: MAX_CACHE_ROWS rows per query
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

### Why MAX_CACHE_ROWS Row Cache Limit?

- ✅ Optimal for LLM token usage and faster interpretation
- ✅ Fast enough for meaningful analysis
- ✅ Reasonable memory footprint
- ✅ Balance between completeness and performance
- ✅ Transparent to users via `data_truncated` flag
- ⚠️ **IMPORTANT**: Interpretation and visualization can ONLY use these MAX_CACHE_ROWS cached rows
- ⚠️ Larger datasets require downloading full CSV for complete analysis

## Code Organization & Constants

### Centralized Configuration (`src/common/constants.py`)

All data limits and chart configurations are centralized in a single source of truth:

```python
# Data limits
MAX_CACHE_ROWS = 30          # Maximum rows cached for interpretation
PREVIEW_ROWS = 30            # Rows shown in preview response
MAX_CHART_BAR_ITEMS = 20     # Maximum bar chart items
MAX_CHART_PIE_SLICES = 8     # Maximum pie chart slices
MAX_SCATTER_POINTS = 100     # Maximum scatter plot points
MAX_LINE_CHART_POINTS = 30   # Maximum line chart data points

# Performance thresholds
LARGE_RESULT_SET_THRESHOLD = 1000  # Smart count optimization threshold
```

**Benefits**:
- ✅ Single source of truth - change once, apply everywhere
- ✅ No hardcoded magic numbers scattered across codebase
- ✅ Consistent limits for charts, caching, and API responses
- ✅ Easy to tune performance vs quality tradeoffs

**Usage**:
```python
from src.common.constants import MAX_CACHE_ROWS, MAX_CHART_BAR_ITEMS

# All modules import from constants.py
chart_data = results[:MAX_CHART_BAR_ITEMS]
cached_data = execute_query(sql, limit=MAX_CACHE_ROWS)
```

### Pipeline Helper Functions (`src/text_to_sql/pipeline/state.py`)

Standardized reasoning log creation to reduce duplication:

```python
def create_success_step(step_name: str, details: str) -> ReasoningStep:
    """Create a successful reasoning step (✅)."""
    return {"step_name": step_name, "details": details, "status": "✅"}

def create_warning_step(step_name: str, details: str) -> ReasoningStep:
    """Create a warning reasoning step (⚠️)."""
    return {"step_name": step_name, "details": details, "status": "⚠️"}

def create_error_step(step_name: str, details: str) -> ReasoningStep:
    """Create an error reasoning step (❌)."""
    return {"step_name": step_name, "details": details, "status": "❌"}
```

**Before** (duplicated across 4 pipeline nodes):
```python
reasoning_log = [{
    "step_name": "SQL Generation",
    "details": "Successfully generated SQL",
    "status": "✅"
}]
```

**After** (consistent, maintainable):
```python
reasoning_log = [create_success_step("SQL Generation", "Successfully generated SQL")]
```

### Performance Optimizations

**Lazy Loading** (`src/text_to_sql/pipeline/nodes/executor.py`):
- Pandas import moved inside CSV export function
- Only loads pandas when CSV export is actually needed
- Faster startup time for non-export operations

```python
def _save_results_to_csv(data: list, query: str) -> str:
    import pandas as pd  # Lazy import - only when needed
    # ... CSV export logic
```

## Configuration

### Environment Variables

```bash
# Required
SCHEMA_ID=sample  # Database identifier (e.g., 'sample', 'neila')
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///data/sample.db  # or postgresql://...
CANONICAL_SCHEMA_PATH=schema_files/sample_schema.json

# Optional - API Performance
CACHE_TTL=600  # seconds (default: 10 minutes)
MAX_CACHE_ROWS=30  # max rows to cache per query
PREVIEW_ROWS=30  # rows returned in preview

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

**Sample Database** (`.env.sample`):
```bash
SCHEMA_ID=sample
DATABASE_URL=sqlite:///data/sample.db
CANONICAL_SCHEMA_PATH=schema_files/sample_schema.json
GEMINI_API_KEY=your_key_here
```

**Neila Database** (`.env.neila`):
```bash
SCHEMA_ID=neila
DATABASE_URL=sqlite:///data/neila.db
CANONICAL_SCHEMA_PATH=schema_files/neila_schema.json
GEMINI_API_KEY=your_key_here
```

**Note**: Cache files are automatically derived from `SCHEMA_ID`:
- Embeddings: `data/{SCHEMA_ID}_embeddings_cache.db`
- SQL Cache: `data/{SCHEMA_ID}_sql_cache.db`

## Error Handling

### Large Dataset Scenarios

**Scenario**: Total rows > MAX_CACHE_ROWS, user requests interpretation

**Behavior**:
- Use cached MAX_CACHE_ROWS rows for analysis
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

## Architecture Overview

### Unified Server Architecture (ADR-023)

The system uses a **unified backend architecture** where all functionality is consolidated in a single FastAPI server:

```
┌─────────────────────────────────────────────────────────────┐
│                    System Architecture                       │
└─────────────────────────────────────────────────────────────┘

Frontend (React - netquery-insight-chat)
  │  Pure React/JavaScript application
  │  Calls backend directly via REST/SSE
  ↓
┌─────────────────────────────────────────────────────────────┐
│           Unified Backend (src/api/server.py)               │
├─────────────────────────────────────────────────────────────┤
│  Chat Layer:                                                │
│    • /chat endpoint (SSE streaming)                         │
│    • Session management                                     │
│    • Conversation context building                          │
│    • Feedback handling with cache invalidation              │
├─────────────────────────────────────────────────────────────┤
│  API Layer:                                                 │
│    • /api/generate-sql (SQL generation)                     │
│    • /api/execute/{id} (query execution)                    │
│    • /api/interpret/{id} (LLM interpretation)               │
│    • /api/schema/overview (schema info)                     │
│    • /api/download/{id} (CSV export)                        │
├─────────────────────────────────────────────────────────────┤
│  Service Layer (src/api/services/):                         │
│    • sql_service.py - SQL generation logic                  │
│    • execution_service.py - Query execution & caching       │
│    • interpretation_service.py - Visualization & insights   │
│    • data_utils.py - Data formatting & pattern analysis     │
├─────────────────────────────────────────────────────────────┤
│  Static Files (optional):                                   │
│    • Serves React build for single-URL deployment           │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│              Text-to-SQL Pipeline (LangGraph)               │
│  Intent → Cache → Schema → SQL Gen → Validate → Execute     │
└─────────────────────────────────────────────────────────────┘
  ↓
Database (SQLite/PostgreSQL)
```

**Key Benefits**:
- **Single deployment**: One Python server handles everything
- **No BFF layer**: Frontend calls backend directly
- **Simpler CORS**: One origin per database
- **Consistent state**: All session management in one place

### Multi-Database Support

Each database runs on its own port with isolated resources:

| Database | Port | Embeddings Cache | SQL Cache |
|----------|------|------------------|-----------|
| sample | 8000 | sample_embeddings_cache.db | sample_sql_cache.db |
| neila | 8001 | neila_embeddings_cache.db | neila_sql_cache.db |

Frontend switches databases by changing the backend URL.

## Frontend Integration

**Note**: Frontend implementation is in [netquery-insight-chat](https://github.com/keo571/netquery-insight-chat)

### Frontend Architecture

The frontend is a **pure React application** with no Python dependencies:

```
netquery-insight-chat/
├── src/
│   ├── components/          # React components
│   │   ├── ChatInterface.js # Main chat UI
│   │   ├── SchemaVisualizer.js # Database diagram (ReactFlow)
│   │   └── ...
│   ├── services/
│   │   └── api.js           # Backend API calls (direct, no BFF)
│   └── App.js               # Root component with database selector
└── public/                  # Static assets
```

**API Service** (`src/services/api.js`):
```javascript
// Database to backend URL mapping
const DATABASE_URLS = {
    'sample': process.env.REACT_APP_SAMPLE_URL || 'http://localhost:8000',
    'neila': process.env.REACT_APP_NEILA_URL || 'http://localhost:8001',
};

// Direct calls to unified backend
export const queryAgent = async (query, sessionId, onEvent, database) => {
    const response = await fetch(`${getApiUrl(database)}/chat`, {...});
    // SSE event handling...
};
```

### Frontend Responsibilities

1. **Query Input**: Natural language query form
2. **SQL Display**: Show generated SQL with syntax highlighting
3. **Data Preview**: Table display (PREVIEW_ROWS rows)
4. **Interpretation Display**: Show insights and findings
5. **Visualization Rendering**: Render charts from viz specs (Recharts)
6. **Download Handling**: CSV file download button
7. **Status Indicators**: Loading states, truncation notices
8. **Schema Visualization**: Interactive database diagram using ReactFlow
9. **Database Switching**: Dropdown to switch between sample/neila databases

### Frontend Data Flow

```
User Input
  ↓
POST /chat (SSE streaming)
  ↓
Display SQL → Show reasoning steps
  ↓
Execute → Show PREVIEW_ROWS row preview + row count
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
    Showing PREVIEW_ROWS of {total_count || 'many'} rows
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

1. Core text-to-SQL pipeline with **7 stages** (LangGraph workflow)
   - Stage 0: Query triage (filter non-DB questions)
   - Stage 1: Cache lookup (two-tier caching with conversational support)
   - Stage 2: Schema analyzer (semantic table discovery + FK expansion)
   - Stage 3: SQL generator (LLM-powered SQL generation)
   - Stage 4: Validator (read-only safety enforcement)
   - Stage 5: Executor (query execution with result caching)
   - Stage 6: Interpreter (optional LLM-powered insights)
2. **Two-tier caching system** with query extraction & rewriting for follow-ups
3. **Conversational query support** with smart rewriting (70-80% cache hit rate)
4. FastAPI server with all endpoints
5. LLM-powered interpretation with structured output (Pydantic schemas)
6. Smart row counting optimization
7. Streaming CSV download
8. Environment profile system (dev/prod)
9. MCP server integration for Claude Desktop
10. Comprehensive testing framework
11. **Centralized constants** for data limits and chart configurations
12. **Standardized helper functions** for reasoning logs
13. **Performance optimizations**: Lazy-loaded imports, reduced code duplication

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
- ✅ Works with multiple databases (via SCHEMA_ID configuration)

## Related Documentation

- [Getting Started](GETTING_STARTED.md) - Setup and usage guide
- [Evaluation](EVALUATION.md) - Testing and evaluation framework
- [Schema Ingestion](SCHEMA_INGESTION.md) - Schema management
- [Sample Queries](SAMPLE_QUERIES.md) - Example queries for testing
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

**Note**: All cache system implementation details are documented in the "Detailed Cache Implementation" section above.

---

## Recent Updates

### 2025-12-11: Unified Server Architecture, Canonical Schema & Service Layer

- ✅ **Unified Server (ADR-023)**: Consolidated chat adapter into backend server
  - Moved session management, SSE streaming, feedback from frontend to `src/api/server.py`
  - Frontend is now pure React/JavaScript (no Python dependencies)
  - Single backend server per database (port 8000 for sample, 8001 for neila)
- ✅ **Canonical Schema as FK Source (ADR-024)**: FK relationships from canonical schema only
  - No database reflection for relationship discovery
  - Frontend schema visualizer uses `relationships` from API
  - Works even when database has no FK constraints
- ✅ **Model Warmup (ADR-025)**: LLM and embedding model warmed up at startup
  - First query is fast (no cold start latency)
  - ~2-3 second startup overhead (one-time)
- ✅ **Service Layer Extraction (ADR-026)**: Extracted shared business logic into services
  - `sql_service.py`: SQL generation logic shared by `/api/generate-sql` and `/chat`
  - `execution_service.py`: Query execution logic shared by `/api/execute` and `/chat`
  - Endpoints are now thin HTTP/SSE wrappers calling service functions
  - Single source of truth for business logic, easier testing
- ✅ **Outbound-only FK Expansion**: Simplified from bidirectional to outbound-only
- ✅ **Pre-built FK Graph**: FK relationships built at startup from canonical schema

### 2025-01-17: Cache System Improvements & Refactoring
- ✅ **Two-Tier Caching**: Embedding cache (partial speedup) + SQL cache (full speedup)
- ✅ **Query Extraction**: Extract current query from conversation context for cache matching
- ✅ **Smart Rewriting**: LLM-based rewriting for ambiguous follow-ups ("which are unhealthy?" → "Show unhealthy servers")
- ✅ **Lazy Rewriting Optimization**: Only rewrite on cache MISS/PARTIAL (skip on FULL HIT for ~10ms response)
- ✅ **Cache Invalidation**: Thumbs down clears SQL but keeps embedding (faster retry: ~2s vs ~2.5s)
- ✅ **Three-Path Routing**: Refactored cache_lookup_node with dedicated handler functions
  - `_handle_full_cache_hit()` - Return SQL immediately (~10ms)
  - `_handle_partial_cache_hit()` - Conditional rewriting logic (~2-2.2s)
  - `_handle_cache_miss()` - Generate from scratch (~2.5-2.7s)
- ✅ **Performance Impact**: 15-25% cache hit rate improvement, 70-80% hit rate with warmup
- ✅ **Files Created**: query_extraction.py, query_rewriter.py, cache_utils.py
- ✅ **Files Updated**: cache_lookup.py, schema_analyzer.py, sql_generator.py, state.py, query_embedding_cache.py

### 2025-01-16: Code Cleanup & Optimization
- ✅ Centralized all data limits and chart configurations to `src/common/constants.py`
- ✅ Created standardized helper functions for reasoning logs
- ✅ Removed ~350 lines of redundant code
- ✅ Implemented lazy-loading for pandas import (performance optimization)
- ✅ Removed dead code exports and unused functions
- ✅ Updated documentation to reflect triage feature and cleanup

### 2025-01-15: Query Triage Feature
- ✅ Added triage node to pipeline (Stage 0)
- ✅ Fast pre-filtering of non-database questions
- ✅ Cost savings: No LLM calls for definition/explanation requests
- ✅ Improved UX with helpful responses and schema suggestions

---

**Last Updated**: 2025-12-11

## Architecture Decision Records

For detailed historical decisions and rationale behind architectural choices, see:
- **[Architecture Decision Records (ADRs)](ARCHITECTURE_DECISION_RECORDS.md)** - Chronological record of all 26 major architectural decisions

Key decisions include:
- **ADR-009**: SQL-Only Cache (simplified from two-tier)
- **ADR-010**: SQLite Schema Embeddings (100x faster than JSON)
- **ADR-011**: Eager Initialization via AppContext (consistent performance)
- **ADR-015**: Dual Backend Implementation (multi-database support)
- **ADR-020**: Conversational Follow-Up Question Handling
- **ADR-022**: Schema Drift Validation on Startup
- **ADR-023**: Unified Server Architecture (chat adapter consolidation)
- **ADR-024**: Canonical Schema as Single Source of Truth for FK Relationships
- **ADR-025**: Model Warmup at Application Startup
- **ADR-026**: Service Layer Extraction (SQL and Execution Services)
