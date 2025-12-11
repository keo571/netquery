# Architecture Decision Records (ADRs)

This document consolidates all major architectural decisions made during NetQuery development.

Each ADR follows this structure:
- **Context**: Problem we faced
- **Decision**: What we chose to do
- **Consequences**: Trade-offs and impacts

---

## ADR-001: Intent Classification System

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
The original pipeline mixed intent classification logic within the cache lookup node, violating the Single Responsibility Principle.

### Decision
Created dedicated `intent_classifier` node as first stage, separating intent classification from caching.

**Architecture**: `START → intent_classifier → [general? → END | sql/mixed? → cache_lookup → ...]`

### Consequences
**Positive**: Single responsibility, better testability, clearer flow
**Negative**: Additional node (minimal ~200ms impact, same as before)

**Files Modified**:
- Created: `src/text_to_sql/pipeline/nodes/intent_classifier.py`
- Modified: `cache_lookup.py`, `graph.py`, `state.py`
- Deleted: `src/text_to_sql/tools/query_embedding_cache.py` (dead code)

---

## ADR-002: Query Rewriting Consolidation

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
Redundant query rewriting in intent classifier (vague "if needed") + cache lookup (fallback).

### Decision
Consolidated ALL rewriting into intent classifier with **mandatory rewriting** for follow-ups.

**Implementation**:
```python
# Intent classifier now ALWAYS rewrites follow-ups
classify_intent(query, full_query=conversation_context)
# → "which are unhealthy?" → "Show all unhealthy servers"

# Cache lookup trusts intent classifier
_handle_cache_miss(query_for_embedding)  # No rewriting needed
```

### Consequences
**Positive**: Single source of truth, -145 lines deleted, ~200ms saved per follow-up
**Negative**: None

---

## ADR-003: State Simplification (Removed cached_sql)

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
State had redundant `cached_sql` + `generated_sql` storing same value.

### Decision
Removed `cached_sql`. Use `cache_hit_type` flag to indicate origin.

**Before**: `{cached_sql: "SELECT...", generated_sql: "SELECT...", cache_hit_type: "full"}`
**After**: `{generated_sql: "SELECT...", cache_hit_type: "full"}`

### Consequences
**Positive**: Simpler state, less memory, clearer semantics
**Negative**: None (internal change)

---

## ADR-004: Progressive Data Disclosure (Mixed Query Support)

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
Mixed queries ("What is DNS? Show all DNS records") processed correctly but general answer never displayed.

### Decision
Modified interpreters to prepend general answers for mixed queries.

**Example Output**:
```markdown
## Answer
DNS is a hierarchical naming system...

---

## SQL Query
SELECT * FROM dns_records

## Results
...
```

### Consequences
**Positive**: Complete answers, better UX, no wasted LLM work
**Negative**: None

**Files**: `interpreter.py`, `interpretation_service.py`, `server.py`

---

## ADR-005: Visualization Performance Optimization

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
Coupled viz selection + interpretation caused 2-5s delay before any visual feedback.

### Decision
Decoupled: (1) Fast viz selection (0ms, rule-based), (2) Async interpretation (LLM-powered)

**Implementation**:
```python
# Instant visualization (no LLM)
viz = select_visualization_fast(query, data, patterns)  # ~0ms

# Async interpretation (LLM)
interpretation = await get_interpretation_only(query, data)  # ~2-5s
```

### Consequences
**Positive**: Instant chart rendering, progressive enhancement, cost savings
**Negative**: Rule-based may be less sophisticated (acceptable tradeoff)

**UX**: Before: Wait 2-5s → After: Instant viz, insights arrive async

---

## ADR-006: Smart LLM Skipping for Trivial Queries

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
Simple list queries ("Show all load balancers") don't benefit from LLM (30% of queries).

### Decision
Added `_is_trivial_query()` to skip LLM when it adds no value.

**Detection**: List queries + single column + no numeric data → Skip LLM

### Consequences
**Positive**: 0ms vs 2-5s for trivial queries, ~$0.001-0.01 saved per query
**Negative**: Heuristic may miss edge cases (low risk)

**Example**: 30 load balancer names → Instant "Found 30 items" (no LLM call)

---

## ADR-007: Frontend Progressive Disclosure API

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
Users need control over execute/interpret/download.

### Decision
Separate endpoints for progressive disclosure:
1. `/api/generate-sql` - SQL only
2. `/api/execute/{id}` - Execute + preview
3. `/api/interpret/{id}` - Interpret + viz (cached data)
4. `/api/download/{id}` - Full CSV

### Consequences
**Positive**: User control, no wasted LLM calls, no redundant SQL execution
**Negative**: Multiple round trips (acceptable for UX)

**Alternative Considered**: Agent tools → Rejected (deferred for MCP)

---

## ADR-008: Keep Current Architecture (Not Switching to Agent Tools)

**Date**: 2025-11-23
**Status**: Decided ✅

### Context
Discussion: Intent classifier vs agent-based tool selection

### Decision
**Keep intent classifier** for web UI.

### Rationale
- **Performance**: Identical (2-3 LLM calls both approaches)
- **Simplicity**: Explicit routing easier to debug
- **Use Case**: Web UI benefits from explicit APIs (ADR-007)
- **No MCP yet**: Tool exposure deferred

### When to Reconsider
- MCP tool exposure needed
- 3+ query types
- Complex multi-tool workflows
- External agents calling NetQuery

### Key Insight
> Intent classifier IS tool selection - same LLM routing, clearer code structure.

---

## ADR-009: SQL-Only Cache (Removed Two-Tier Caching)

**Date**: 2025-01-17
**Status**: Implemented ✅

### Context
Previous two-tier cache (embedding + SQL) had complexity without justification:
- Partial hits only helped thumbs-down retries (~5-10% of cases)
- Saved 500ms in rare case (2s vs 2.5s)
- Questionable assumption: "table selection usually correct"
- Risk of keeping wrong embeddings after thumbs-down

### Decision
Simplified to **SQL-only cache**: SQLite database storing only generated SQL.

**New Schema**:
```sql
CREATE TABLE sql_cache (
    normalized_query TEXT UNIQUE,
    generated_sql TEXT NOT NULL,  -- Always present
    created_at TIMESTAMP,
    hit_count INTEGER DEFAULT 1
)
```

**Two cache states** (not three):
- **HIT**: Have SQL (~10ms) → Skip to validator
- **MISS**: Generate from scratch (~2.5s) → Run full pipeline

### Consequences
**Positive**: ~500 lines removed, clearer mental model, more robust retry
**Negative**: +500ms on thumbs-down retry (rare case, 5-10% of queries)

**Trade-off**: Massive simplification for negligible performance cost in edge case

**Files**: Created `sql_cache.py`, simplified `cache_lookup.py`, `schema_analyzer.py`, `sql_generator.py`

---

## ADR-010: SQLite Schema Embeddings (Not JSON Files)

**Date**: 2025-01-17
**Status**: Implemented ✅

### Context
Schema embeddings stored as individual JSON files had performance issues:
- Large JSON rewrites on every update (O(n))
- No indexing for lookups
- File locking issues with concurrent access
- Inconsistent with SQL query cache design

### Decision
Migrated to **SQLite storage** for schema embeddings.

**Implementation**:
```sql
CREATE TABLE schema_embeddings (
    namespace TEXT NOT NULL,
    table_name TEXT NOT NULL,
    embedding BLOB NOT NULL,  -- Pickle-serialized numpy array
    UNIQUE(namespace, table_name)
)
```

**Storage location**: `data/{SCHEMA_ID}_embeddings_cache.db`

### Consequences
**Positive**:
- 100x faster writes (O(1) INSERT vs O(n) file rewrite)
- 10-100x faster lookups (indexed)
- Better concurrent access (SQLite handles locking)
- Consistent architecture (both caches use SQLite)
- Standard debugging (sqlite3 CLI)

**Negative**: None (pure improvement)

**Migration**: Automatic rebuild on first use, no manual steps needed

---

## ADR-011: Eager Initialization (No Lazy Loading)

**Date**: 2025-01-19
**Status**: Implemented ✅

### Context
Lazy initialization caused 3-5s delay on **first user request**:
- LLM client init (~2-3s)
- Embedding model init (~1-2s)
- Database pool setup

Poor UX: First user gets slow experience, subsequent users fast.

### Decision
**Eager initialization** of all resources at app startup via `AppContext`.

**Implementation**:
```python
class AppContext:
    def __init__(self):
        """Auto-initialize all resources immediately."""
        self._initialize_resources()  # Runs on startup

    def get_llm(self):
        return self._llm  # Simple property access, 0ms overhead
```

### Consequences
**Positive**:
- First request is fast (0ms init overhead)
- Consistent performance across all requests
- Fail-fast: Errors caught at startup, not on first request
- Simpler code: No lazy checks, simple getters

**Negative**: +3-5s startup time (one-time cost, acceptable)

**Trade-off**: Slower startup for better user experience and simpler code

---

## ADR-012: Schema Ingestion Format with Sample Values

**Date**: 2025-11-20
**Status**: Implemented ✅

### Context
Schema required rich descriptions for semantic search, but lacked representative values for LLM context (e.g., "status" could be what values?).

### Decision
**Canonical JSON schema** with optional `sample_values` field.

**Input**: Excel with `table_schema` + `mapping` + `suggested_queries` sheets
**Output**: JSON with embedded sample values

**Example**:
```json
{
  "status": {
    "data_type": "varchar",
    "description": "Current operational status",
    "sample_values": ["active", "inactive", "maintenance"]
  }
}
```

**Sample values**:
- Added to Excel as comma-separated string
- Auto-parsed to JSON array during ingestion
- Appears inline in LLM prompts for better context

### Consequences
**Positive**:
- Better LLM context (knows valid enum values)
- Faster SQL generation (fewer guesses)
- Pure canonical schema (no DB introspection during queries)
- Drift detection validates schema matches DB

**Negative**: Manual maintenance of sample values (low effort)

**Files**: `schema_ingestion/excel_parser.py`, `schema_ingestion/canonical.py`

---

## ADR-013: Code Quality Refactoring (Single Responsibility)

**Date**: 2025-11-23
**Status**: Implemented ✅

### Context
Codebase had accumulated dead code, duplicated singletons, and hardcoded values.

### Decision
Major cleanup pass focused on simplification:

**Changes**:
1. **Deleted dead code**: `triage.py`, `sql_generation.py`, `result_interpretation.py`, `prompts/__init__.py`
2. **Consolidated singletons**: All through `AppContext` (removed 3 separate patterns)
3. **Centralized constants**: Moved magic numbers to `constants.py`
4. **Split complex functions**:
   - `cache_lookup_node()` → 3 focused functions
   - `_build_schema_context()` → extracted header builder
5. **Fixed broken import**: MCP server had wrong import path

### Consequences
**Positive**:
- -200 lines of dead/duplicate code
- Single source of truth for singletons
- All magic numbers in one place
- Better function testability
- Fixed critical MCP server bug

**Negative**: None (pure improvement)

**Impact**: No breaking changes, all internal refactoring

---

## ADR-014: MVP Improvements (JSON Parsing + Prompts)

**Date**: 2025-11-22
**Status**: Implemented ✅

### Context
LLM occasionally returned JSON in markdown code blocks or with extra text, causing parsing failures.

### Decision
Added robust JSON cleanup without abstraction layers:

**Implementation**:
```python
def cleanup_json_response(text):
    # Remove markdown code blocks
    # Extract outermost {...} object
    # Return clean JSON string
```

**Improved prompts**:
- "CRITICAL: Your response must be ONLY valid JSON"
- Single-line format specification
- Clear examples over verbose rules

### Consequences
**Positive**:
- +15% parsing reliability
- Better LLM compliance
- ~0ms overhead (simple regex)
- Added performance logging (visibility)

**Negative**: None

**Vertex AI compatible**: Manual JSON parsing works everywhere (no dependency on `with_structured_output()`)

---

## ADR-015: Dual Backend Implementation

**Date**: 2025-11-26
**Status**: Implemented ✅

### Context
NetQuery needed to support multiple databases (sample and neila) that users could switch between via a frontend. Dynamic database switching within a single backend would require AppContext reloading and state management complexity.

### Decision
Implemented **dual backend instances** approach: Run separate backend processes for each database on different ports.

**Architecture**:
- Sample database: `http://localhost:8000` (SCHEMA_ID=sample)
- Neila database: `http://localhost:8001` (SCHEMA_ID=neila)
- Frontend switches by changing backend URL

**Implementation**:
- Created `.env.sample` and `.env.neila` configuration files
- Created `start-dual-backends.sh` script to launch both backends
- Added command-line argument support to `src/api/server.py` (--port, --host, --reload)
- Each database has isolated caches: `data/{SCHEMA_ID}_embeddings_cache.db`, `data/{SCHEMA_ID}_sql_cache.db`

### Consequences
**Positive**:
- Instant switching (no AppContext reload delays)
- Complete isolation (no risk of data cross-contamination)
- Simpler backend (no dynamic switching logic)
- Easier debugging (separate logs per database)
- Better performance (no resource contention)
- Scalable (easy to add more databases)

**Negative**:
- Requires running multiple processes
- Uses multiple ports
- Slightly more memory usage (one process per database)

**Trade-off**: For most use cases with 2-3 databases, benefits far outweigh drawbacks.

**Files**:
- Created: `.env.sample`, `.env.neila`, `start-dual-backends.sh`, `docs/ADDING_NEW_DATABASE.md`
- Modified: `src/api/server.py` (added CLI args), `src/api/app_context.py` (fixed circular dependency)

---

## ADR-016: Repository Cleanup (Simplified Naming)

**Date**: 2025-11-26
**Status**: Implemented ✅

### Context
Repository had confusing naming where "dev/prod" terminology conflicted with actual database names ("sample" and "neila"). The `.env.dev` file was a duplicate of `.env.sample`, both pointing to sample.db.

### Decision
**Simplified naming** to align with database identifiers:
- Renamed `start-dev.sh` → `setup-sample.sh` (clarifies it sets up sample database)
- Removed `.env.dev` (duplicate of `.env.sample`)
- Updated all documentation to use database-oriented terminology
- Marked `profile.sh` as legacy (backward compatibility only)

**Terminology Changes**:
- OLD: "Dev mode" / "Prod mode" → Implied environment types
- NEW: "Sample database" / "Neila database" → Actual database names
- OLD: `NETQUERY_ENV=dev` → Conflicted with database names
- NEW: `SCHEMA_ID=sample` / `SCHEMA_ID=neila` → Clear namespace identifier

### Consequences
**Positive**:
- Clearer purpose (setup-sample.sh obviously sets up sample database)
- Consistent naming (database names, env files, schema IDs all align)
- Reduced redundancy (removed duplicate .env.dev file)
- Better documentation (matches actual usage)

**Negative**: None (backward compatible via profile.sh)

**Files**:
- Renamed: `start-dev.sh` → `setup-sample.sh`
- Deleted: `.env.dev`
- Modified: `setup-sample.sh` (uses `.env.sample` instead of `.env.dev`)
- Updated: `docs/GETTING_STARTED.md`, `README.md`

---

## ADR-017: Dual Backends Development Mode

**Date**: 2025-11-26
**Status**: Implemented ✅

### Context
The `start-dual-backends.sh` script was designed for production use (background processes, hidden logs) making it inconvenient for backend development where auto-reload and visible logs are essential.

### Decision
Added **`--dev` flag** to `start-dual-backends.sh` supporting two modes:

**Production Mode** (default):
```bash
./start-dual-backends.sh
```
- Runs both backends in background
- Logs go to `/tmp/netquery_sample.log` and `/tmp/netquery_neila.log`
- No auto-reload
- Perfect for: Frontend integration, demos, production-like testing

**Development Mode** (new):
```bash
./start-dual-backends.sh --dev
```
- Runs both backends with `--reload` flag
- Logs appear directly in terminal
- Auto-reloads when Python files change
- Perfect for: Backend development, debugging, active coding

### Consequences
**Positive**:
- Flexible for both development and production workflows
- Auto-reload saves time during development
- Visible logs improve debugging
- No breaking changes (default behavior unchanged)

**Negative**: None

**Comparison**:
| Feature | Production Mode | Development Mode | Manual Start |
|---------|-----------------|------------------|--------------|
| **Backends** | 2 (sample + neila) | 2 (sample + neila) | 1 (specified via SCHEMA_ID) |
| **Auto-reload** | ❌ No | ✅ Yes | ✅ Yes (with --reload) |
| **Logs visible** | ❌ No (in `/tmp/`) | ✅ Yes (terminal) | ✅ Yes (terminal) |
| **Background** | ✅ Yes | ❌ No (foreground) | ❌ No (foreground) |
| **Command** | `./start_dual_backends.sh` | `./start_dual_backends.sh --dev` | `SCHEMA_ID=sample python -m src.api.server --port 8000` |

**Files**: Modified `start-dual-backends.sh`

---

## ADR-018: Environment File Simplification (.env.prod Removal)

**Date**: 2025-11-26
**Status**: Implemented ✅

### Context
`.env.prod` was for PostgreSQL database configuration but the user's setup exclusively uses SQLite databases (sample and neila). The file contained outdated configuration and added unnecessary complexity.

### Decision
**Removed `.env.prod`** and updated documentation to reflect SQLite-only architecture.

**Rationale**:
- User only needs SQLite databases (sample and neila)
- `.env.prod` was for PostgreSQL (different database type)
- Contained outdated references to old setup scripts
- Added confusion with old `NETQUERY_ENV` approach
- Simplified architecture uses only `SCHEMA_ID` for database switching

### Consequences
**Positive**:
- Clearer repository (only relevant config files)
- No confusion between PostgreSQL and SQLite setups
- Consistent with simplified `SCHEMA_ID` approach
- Easier onboarding for new users

**Negative**: None (PostgreSQL users can create custom config if needed)

**Current Environment Files**:
| File | Purpose | Database |
|------|---------|----------|
| `.env.sample` | Sample/demo database | SQLite (sample.db) |
| `.env.neila` | Customer database | SQLite (neila.db) |
| `.env` | Active config (auto-generated) | Depends on which config is copied |

**Files**:
- Deleted: `.env.prod`
- Updated: `docs/GETTING_STARTED.md`, `README.md`

---

## ADR-019: Required Visualization-Focused Suggested Queries

**Date**: 2025-11-28
**Status**: Implemented ✅

### Context

The system initially auto-generated generic query suggestions based on table names (e.g., "Show recent load balancers records"). These suggestions were:
- Generic and not user-friendly
- Didn't leverage domain knowledge (sample values, real use cases)
- Not optimized for visualizations (bar charts, pie charts, line charts)
- Optional (allowed missing suggestions)

Users needed better guidance on what questions to ask, especially for different visualization types.

### Decision

Made `suggested_queries` sheet **required** in Excel schema files with visualization-focused queries.

**Requirements**:
1. **Required sheet**: All Excel schemas must include `suggested_queries` sheet
2. **Validation**: Schema ingestion fails if sheet is missing or empty
3. **Visualization types**: Queries must support different chart types:
   - **Bar charts**: Count/aggregation (e.g., "Show count of X by Y")
   - **Pie charts**: Distribution (e.g., "Show distribution of X by Y")
   - **Line charts**: Time series with explicit date ranges (e.g., "Show X over the last 30 days")
   - **Tables**: List/detail queries (e.g., "Show all active X")

**Implementation**:
- Updated Excel parser to require `suggested_queries` sheet
- Removed auto-generation fallback
- Added 15 visualization-focused queries to sample database
- Updated canonical schema format to store suggestions

### Consequences

**Positive**:
- **Better UX**: Natural, domain-specific questions instead of generic templates
- **Visualization-ready**: Queries designed for specific chart types
- **Leverages domain knowledge**: Uses sample values and real use cases
- **Onboarding**: Helps new users understand what questions to ask
- **Consistency**: All schemas provide intentional, curated suggestions
- **Time-aware**: Line chart queries use explicit date ranges (last 30 days)

**Negative**:
- **Breaking change**: Existing schemas without suggestions must be updated
- **Manual effort**: Requires schema authors to think about good queries

**Trade-off**: Better UX and intentional design worth the migration effort.

**Files**:
- Modified: `src/schema_ingestion/excel_parser.py` (required sheet)
- Modified: `src/schema_ingestion/canonical.py` (store suggestions)
- Modified: `src/common/schema_summary.py` (removed fallback)
- Updated: `schema_files/sample_schema.xlsx` (15 queries)
- Created: `scripts/add_suggested_queries_to_excel.py` (helper)

---

## ADR-020: Conversational Follow-Up Question Handling

**Date**: 2025-11-28
**Status**: Implemented ✅

### Context

Users ask follow-up questions in chat interfaces (e.g., "Show servers" → "which are unhealthy?"). The system needed to:
1. Understand ambiguous follow-ups that reference previous context
2. Cache queries efficiently (original vs rewritten)
3. Support mixed intents (general knowledge + database queries)
4. Handle conversation history from frontend chat adapter

### Decision

Implemented a **3-phase intelligent pipeline** for follow-up question handling:

**Phase 1: Query Extraction**
- Frontend sends conversation context with marker: `USER'S NEW QUESTION: which are unhealthy?`
- Extract current query from full context for cache matching
- Strip conversation history noise

**Phase 2: Intent Classification + Query Rewriting**
- **LLM-powered classification** with 3 intent types:
  - `sql`: Pure database query → Continue to cache
  - `general`: Knowledge question → Answer directly (skip SQL pipeline)
  - `mixed`: Both general + SQL → Provide both answer and data
- **Smart rewriting** for ambiguous follow-ups using conversation context
  - Input: "which are unhealthy?" (follow-up)
  - Context: Previous question "Show servers"
  - Output: "Show all unhealthy servers" (standalone query)
- LLM sees full conversation history + schema context for accurate rewriting

**Phase 3: Smart Cache Lookup**
- Uses rewritten query from intent classifier
- Cache HIT → Skip schema analysis + SQL generation (~2-3s saved)
- Cache MISS → Continue to schema analyzer

### Consequences

**Positive**:
- **Natural conversation**: Understands ambiguous follow-ups like "which ones", "show more", "remove column x"
- **Fast responses**: Cache lookup with rewritten queries (~200ms LLM + ~10ms cache)
- **Accurate context**: LLM rewriting uses full conversation history + schema
- **Mixed intent support**: Handles both knowledge questions and data queries
- **Lazy rewriting**: Only rewrites when needed (before cache lookup)

**Negative**:
- **LLM dependency**: Requires ~200ms LLM call for every query (even first ones)
- **Cost**: LLM API costs for intent classification

**Performance**:
- First query (cache miss): ~2-5s
- Follow-up (cache hit after rewrite): ~200ms (LLM) + ~10ms (cache)
- Follow-up (cache miss): ~200ms (LLM) + ~2-5s (SQL gen)
- General question: ~200ms (LLM only, skip SQL pipeline)

**Trade-off**: 200ms LLM overhead worth it for accurate understanding and fast cached follow-ups.

**Files**:
- Created: `src/text_to_sql/utils/query_extraction.py` (extract current query)
- Created: `src/text_to_sql/utils/query_rewriter.py` (LLM classification + rewriting)
- Created: `src/text_to_sql/pipeline/nodes/intent_classifier.py` (pipeline node)
- Modified: `src/text_to_sql/pipeline/nodes/cache_lookup.py` (use rewritten query)
- Modified: `src/text_to_sql/pipeline/state.py` (track intent + rewritten queries)

---

## ADR-021: CLI AppContext Integration for Consistency

**Date**: 2025-11-27
**Status**: Implemented ✅

### Context

After refactoring to remove the `get_analyzer()` wrapper function, the CLI would break because:
- The `schema_analyzer()` node calls `AppContext.get_instance().get_schema_analyzer()`
- AppContext was only initialized in the API server, not in the CLI
- Running the CLI would cause an error when trying to access uninitialized AppContext

**Architecture Before**:
- **API server**: Initialized AppContext on startup (shared resources)
- **CLI**: No AppContext, initialized resources on-demand per query
- **Problem**: Different code paths, maintenance burden, inconsistent behavior

### Decision

Added **AppContext initialization to CLI** (`gemini_cli.py`) before running the pipeline.

**Implementation**:
```python
# Initialize AppContext singleton (same as API server)
# This initializes all resources: LLM, embeddings, caches, schema analyzer
from src.api.app_context import AppContext
print("Initializing resources...")
ctx = AppContext.get_instance()
```

**Placement**: After argument parsing and environment variable overrides, before query processing

**Benefits**:
1. **Consistency**: CLI and API server use exactly the same code path
2. **Shared Resources**:
   - LLM client reused across all queries in a session
   - Embedding service: Single instance for all table lookups
   - Embedding store: SQLite-backed semantic table finder
   - SQL cache: Query results cached within session
   - Schema analyzer: Single instance with pre-loaded schema
3. **Better Performance (Within Session)**:
   - First query: ~2-5s (initialization + query)
   - Subsequent queries: Faster due to caching
   - Resources initialized once, reused for all queries
4. **Simpler Codebase**: Single initialization pattern, no CLI-specific workarounds

### Consequences

**Positive**:
- **Single code path**: Easier maintenance, all features work in both CLI and API
- **Resource reuse**: Amortized initialization cost over multiple queries
- **No special cases**: No CLI-specific workarounds needed

**Negative**:
- **Slower startup**: CLI takes 3-5s to initialize AppContext on startup
  - **Before**: Instant startup, on-demand initialization
  - **After**: 3-5s one-time initialization cost per CLI invocation
- **Impact on scripts**: Each CLI invocation pays the initialization cost

**Trade-off**: Slower startup (~3-5s) for consistency and simplicity

**When This Matters**:
- **Interactive sessions**: Initialization cost amortized over multiple queries (good!)
- **Single queries**: Each run pays the initialization cost (acceptable)
- **Scripts**: Multiple CLI invocations each pay initialization cost (consider using API instead)

**Files Modified**:
- Modified: `gemini_cli.py` (added AppContext initialization)
- Related: `src/api/app_context.py` (AppContext singleton)
- Related: `src/text_to_sql/pipeline/nodes/schema_analyzer.py` (uses AppContext)

---

## ADR-022: Schema Drift Validation on Startup

**Date**: 2025-11-28
**Status**: Implemented ✅

### Context

The canonical schema (JSON file) defines the expected database structure, but the actual database can drift over time:
- Developers may alter database schema without updating the JSON
- DBAs may drop/rename columns
- Schema files may be copied between environments without updating the actual database

This drift causes runtime errors when:
- SQL generation references non-existent tables/columns
- Semantic table finder expects tables that don't exist
- Users get confusing error messages during query execution

### Decision

Implemented **schema drift validation** that runs automatically at application startup (in `AppContext._validate_schema_drift()`).

**Implementation**:
```python
def _validate_schema_drift(self):
    """
    Validate that canonical schema matches actual database schema.

    Checks that all tables and columns defined in the canonical schema
    exist in the actual database. Does NOT require database to have ONLY
    those tables/columns - it's fine if the database has extras.

    Raises:
        ValueError: If any table or column from canonical schema is missing
    """
    # For each table in canonical schema:
    #   1. Check table exists in database
    #   2. Get actual columns from database
    #   3. Check each canonical column exists
    # Report errors and raise if mismatches found
```

**Validation Logic**:
1. **Table Validation**: Every table in canonical schema must exist in database
2. **Column Validation**: Every column in canonical schema must exist in database
3. **One-Way Check**: Database can have extra tables/columns (not an error)
4. **Fail-Fast**: Application startup fails if drift detected
5. **Clear Errors**: Detailed error messages show which tables/columns are missing

**Example Error**:
```
Schema drift detected (2 mismatches):
  ❌ Table 'old_table' defined in canonical schema but not found in database
  ❌ Column 'servers.old_column' defined in canonical schema but not found in database

Your canonical schema defines tables/columns that don't exist in the database.
Please update the canonical schema or fix the database schema.
```

**When It Runs**:
- **API Server**: Validates on startup (in `lifespan` event handler)
- **CLI**: Validates when `AppContext.get_instance()` is called
- **Timing**: During `AppContext._initialize_resources()` (after schema analyzer init)

### Consequences

**Positive**:
- **Fail-fast**: Catches schema mismatches at startup, not during user queries
- **Clear errors**: Detailed messages show exactly what's missing
- **Prevents confusion**: Users don't get obscure SQL errors at runtime
- **Developer-friendly**: Forces developers to keep canonical schema in sync
- **Zero runtime overhead**: Validation only runs once at startup

**Negative**:
- **Slower startup**: +200-500ms for database introspection
- **Breaking changes**: Outdated schemas cause startup failure (this is intentional!)
- **One-way validation**: Doesn't detect if database has tables not in canonical schema

**Trade-off**: Slight startup delay for much better error prevention and developer experience.

**Use Cases**:
1. **Environment Mismatch**: Sample schema deployed to production database
2. **Incomplete Migration**: Database schema updated but JSON not regenerated
3. **Typos**: Column name misspelled in Excel schema file
4. **Schema Evolution**: Database evolved but canonical schema not updated

**Resolution Steps**:
When validation fails, developers must:
1. Check which tables/columns are missing (see error message)
2. Either:
   - **Option A**: Update database schema to match canonical schema
   - **Option B**: Regenerate canonical schema from updated Excel file
   - **Option C**: Fix typos in Excel schema and re-run schema ingestion

**Files**:
- Implemented: `src/api/app_context.py` (`_validate_schema_drift()` method)
- Related: `src/text_to_sql/tools/database_toolkit.py` (provides `get_table_names()`, `get_table_info()`)

---

## ADR-023: Unified Server Architecture (Chat Adapter Consolidation)

**Date**: 2025-12-11
**Status**: Implemented ✅

### Context

The original architecture had a **separate chat adapter** (BFF - Backend for Frontend) layer:

**Before**:
```
Frontend (React)
     ↓
Chat Adapter (netquery-insight-chat/chat_adapter.py)  ← BFF Layer
     ↓
Backend API (netquery/src/api/server.py)
     ↓
Text-to-SQL Pipeline
```

Problems with this approach:
- **Two Python servers** needed for full functionality
- **Deployment complexity**: Frontend repo needed to run Python code
- **Code duplication**: Session management in both repos
- **Maintenance burden**: Changes required syncing between repos
- **CORS complexity**: Cross-origin requests between BFF and backend

### Decision

**Unified all functionality into a single backend server** (`src/api/server.py`).

**After**:
```
Frontend (React - pure JS/static files)
     ↓
Unified Backend (netquery/src/api/server.py)
  ├── Chat endpoints (/chat, SSE streaming)
  ├── API endpoints (/api/generate-sql, /api/execute, etc.)
  ├── Session management
  ├── Feedback handling
  └── Static file serving (optional)
     ↓
Text-to-SQL Pipeline
```

**Key Changes**:

1. **Moved from frontend to backend**:
   - Session management (`sessions` dict, `get_or_create_session()`)
   - Conversation context building (`build_context_prompt()`)
   - SSE streaming (`/chat` endpoint with `StreamingResponse`)
   - Feedback endpoint with cache invalidation

2. **Frontend simplified to pure React**:
   - `api.js` calls backend directly (no Python BFF)
   - Database switching via backend URL mapping
   - No Python dependencies in frontend

3. **Single-URL deployment**:
   - Backend serves both API and static files
   - One port per database (8000 for sample, 8001 for neila)

### Implementation

**Server structure** (`src/api/server.py`):
```python
"""
FastAPI server for Netquery Text-to-SQL system.

This is the unified server that combines:
- Core SQL generation and execution (original server.py)
- Chat adapter functionality (session management, streaming, feedback)
- Static file serving for React frontend

Single URL deployment: All services from one server.
"""

# SESSION MANAGEMENT (from chat_adapter)
sessions: Dict[str, Dict[str, Any]] = {}

# Chat-specific models (from chat_adapter)
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    database: str = "sample"

# CHAT ENDPOINTS (from chat_adapter)
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # SSE streaming response
    return StreamingResponse(
        stream_response(request),
        media_type="text/event-stream"
    )
```

**Frontend API** (`netquery-insight-chat/src/services/api.js`):
```javascript
// Database to backend URL mapping
const DATABASE_URLS = {
    'sample': process.env.REACT_APP_SAMPLE_URL || 'http://localhost:8000',
    'neila': process.env.REACT_APP_NEILA_URL || 'http://localhost:8001',
};

// Direct calls to unified backend (no BFF layer)
export const queryAgent = async (query, sessionId, onEvent, database) => {
    const response = await fetch(`${getApiUrl(database)}/chat`, {
        method: 'POST',
        body: JSON.stringify({ message: query, session_id: sessionId, database })
    });
    // SSE event handling...
};
```

### Consequences

**Positive**:
- **Simpler deployment**: One Python server (backend only)
- **Reduced latency**: No extra hop through BFF layer
- **Easier maintenance**: All Python code in one repo
- **Better separation**: Frontend is pure React/JS
- **Consistent state**: Session management in one place
- **Simpler CORS**: Frontend only talks to one origin per database

**Negative**:
- **Larger server.py**: ~1000 lines (manageable with good organization)
- **Backend complexity**: Handles both API and chat logic

**Trade-off**: Slightly larger backend file for much simpler overall architecture.

### Migration Path

1. ✅ Copied session management to `src/api/server.py`
2. ✅ Added `/chat` endpoint with SSE streaming
3. ✅ Added feedback endpoint with cache invalidation
4. ✅ Updated frontend `api.js` to call backend directly
5. ✅ Removed `chat_adapter.py` from frontend repo
6. ✅ Frontend repo now contains only React code

**Files**:
- Modified: `src/api/server.py` (added chat adapter functionality)
- Modified: `netquery-insight-chat/src/services/api.js` (direct backend calls)
- Deleted: `netquery-insight-chat/chat_adapter.py` (no longer needed)

---

## ADR-024: Canonical Schema as Single Source of Truth for FK Relationships

**Date**: 2025-12-11
**Status**: Implemented ✅

### Context

The FK (foreign key) relationship graph was being built from two sources:
1. **Database introspection**: SQLAlchemy reflecting actual FK constraints
2. **Canonical schema**: JSON file with defined relationships

This caused issues:
- **Missing relationships**: Databases without explicit FK constraints showed no relationships
- **Inconsistency**: Frontend schema visualizer showed different relationships than backend used
- **Performance**: Full database reflection at startup (~500ms)

### Decision

**Use canonical schema as the single source of truth** for FK relationships.

**Implementation**:
1. **FK graph pre-built at startup** from canonical schema
2. **No database reflection** for relationship discovery
3. **Outbound-only FK expansion** (simplified from bidirectional)
4. **Frontend receives relationships** from `/api/schema/overview` endpoint

**Code changes**:

```python
# src/api/app_context.py
def _prebuild_fk_graph(self):
    """Pre-build FK relationship graph from canonical schema."""
    canonical = self._schema_analyzer.canonical_schema
    for table in canonical.get('tables', []):
        for rel in table.get('relationships', []):
            # Build outbound relationships only
            self._fk_graph[table['name']].add(rel['referenced_table'])

# src/text_to_sql/tools/database_toolkit.py
def get_outbound_relationships(self) -> Dict[str, set]:
    """Get FK relationships (outbound only) from canonical schema."""
    # Returns {table_name: {referenced_tables}}
```

**Schema overview response** includes relationships:
```python
# src/api/server.py
class SchemaOverviewTable(BaseModel):
    name: str
    columns: List[ColumnInfo]
    relationships: List[TableRelationship]  # From canonical schema
```

### Consequences

**Positive**:
- **Consistent relationships**: Same source for backend and frontend
- **Faster startup**: No FK reflection from database
- **Works without DB FKs**: Relationships defined in canonical schema work even if database has no FK constraints
- **Simpler code**: One source of truth, no merging logic

**Negative**:
- **Manual maintenance**: Relationships must be defined in Excel schema
- **No auto-discovery**: Database FK changes not auto-detected

**Trade-off**: Manual relationship definition for reliability and consistency.

**Files**:
- Modified: `src/api/app_context.py` (`_prebuild_fk_graph()`)
- Modified: `src/text_to_sql/tools/database_toolkit.py` (`get_outbound_relationships()`)
- Modified: `src/api/server.py` (include relationships in schema overview)
- Modified: `netquery-insight-chat/src/components/SchemaVisualizer.js` (use `relationships` from API)

---

## ADR-025: Model Warmup at Application Startup

**Date**: 2025-12-11
**Status**: Implemented ✅

### Context

First query after server start was slow (~5-8 seconds) because:
- LLM connection not established until first use
- Embedding model weights not loaded
- Cold start latency visible to first user

### Decision

**Warmup LLM and embedding model** during application startup (in `AppContext._initialize_resources()`).

**Implementation**:
```python
def _warmup_models(self):
    """Warmup LLM and embedding model with simple requests."""
    import time

    # Warmup embedding model
    try:
        start = time.time()
        self._embedding_service.embed_query("warmup")
        logger.info(f"  Embedding model warmed up ({(time.time()-start)*1000:.0f}ms)")
    except Exception as e:
        logger.warning(f"  Embedding warmup failed: {e}")

    # Warmup LLM
    try:
        start = time.time()
        self._llm.invoke("Say 'ready' in one word.")
        logger.info(f"  LLM warmed up ({(time.time()-start)*1000:.0f}ms)")
    except Exception as e:
        logger.warning(f"  LLM warmup failed: {e}")
```

### Consequences

**Positive**:
- **First query fast**: No cold start latency for first user
- **Consistent performance**: All queries have similar response times
- **Fail-fast**: Connection issues caught at startup, not first request

**Negative**:
- **Slower startup**: +2-3 seconds at application start
- **API costs**: Small warmup requests cost a few tokens

**Trade-off**: Slightly slower startup for better user experience.

**Files**:
- Modified: `src/api/app_context.py` (`_warmup_models()` method)

---

## ADR-026: Service Layer Extraction (SQL and Execution Services)

**Date**: 2025-12-11
**Status**: Implemented ✅

### Context

The `/api/*` REST endpoints and `/chat` SSE endpoint had **duplicate business logic**:

1. **SQL generation**: Same `text_to_sql_graph.ainvoke()` call in both places
2. **Query execution**: Same count-checking, LIMIT handling, data formatting in both places
3. **Visualization**: Same pattern analysis and chart selection (already extracted to `interpretation_service.py`)

This duplication meant:
- Bug fixes needed in multiple places
- Risk of logic divergence between endpoints
- Harder to test business logic in isolation
- `server.py` was growing large (~1000 lines)

### Decision

**Extract shared business logic into service modules**, keeping endpoints as thin HTTP/SSE wrappers.

**New Service Structure**:
```
src/api/services/
├── sql_service.py           # NEW: generate_sql()
├── execution_service.py     # NEW: execute_sql()
├── interpretation_service.py # Existing: get_visualization_for_data()
└── data_utils.py            # Existing: format_data_for_display()
```

**sql_service.py**:
```python
@dataclass
class SQLGenerationResult:
    sql: Optional[str]
    intent: str  # "sql", "general", or "mixed"
    general_answer: Optional[str]
    schema_overview: Optional[Dict]
    error: Optional[str] = None

async def generate_sql(query, text_to_sql_graph, get_schema_overview_fn) -> SQLGenerationResult:
    """Generate SQL from natural language query."""
    result = await text_to_sql_graph.ainvoke({...})
    return SQLGenerationResult(sql=result.get("generated_sql"), ...)
```

**execution_service.py**:
```python
@dataclass
class ExecutionResult:
    data: List[Dict]
    columns: List[str]
    total_count: Optional[int]
    error: Optional[str] = None

def execute_sql(sql, engine, max_rows, count_threshold) -> ExecutionResult:
    """Execute SQL and return formatted results."""
    # Count checking, LIMIT handling, data formatting
    return ExecutionResult(data=formatted_data, ...)
```

**Endpoint usage** (both `/api/generate-sql` and `/chat` now use):
```python
from .services.sql_service import generate_sql
from .services.execution_service import execute_sql

result = await generate_sql(query, text_to_sql_graph, get_schema_overview)
exec_result = execute_sql(result.sql, engine, MAX_CACHE_ROWS, THRESHOLD)
```

### Consequences

**Positive**:
- **Single source of truth**: SQL generation and execution logic in one place
- **Easier testing**: Services can be unit tested without HTTP layer
- **Cleaner endpoints**: HTTP handlers focus on request/response, not business logic
- **Reduced duplication**: ~80 lines of duplicate code removed from `server.py`

**Negative**:
- **More files**: 2 new service files to maintain
- **More imports**: Endpoints import from services

**Trade-off**: Slightly more files for better separation of concerns and maintainability.

**Files**:
- Created: `src/api/services/sql_service.py`
- Created: `src/api/services/execution_service.py`
- Modified: `src/api/server.py` (refactored endpoints to use services)

---

**Last Updated**: 2025-12-11
