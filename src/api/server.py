"""
Unified FastAPI server for Netquery Text-to-SQL system.

Provides:
- Chat endpoint with SSE streaming (/chat)
- SQL generation and execution APIs (/api/*)
- Session management for conversational queries
- Feedback handling with cache invalidation
- Static file serving for React frontend (optional)

Single URL deployment: All services from one server per database.
"""

# ================================
# IMPORTS
# ================================

import uuid
import logging
import asyncio
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from io import StringIO
from src.common.env import load_environment
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables before importing pipeline components
load_environment()

from src.common.database.engine import get_engine
from src.common.schema_summary import get_schema_overview
from src.text_to_sql.pipeline.graph import text_to_sql_graph
from src.api.app_context import initialize_app_context, cleanup_app_context

# ================================
# CONFIGURATION & SETUP
# ================================

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# CACHE MANAGEMENT
# ================================

# In-memory cache for query results
query_cache: Dict[str, Dict[str, Any]] = {}

# ================================
# SESSION MANAGEMENT
# ================================

# Session storage (in-memory)
sessions: Dict[str, Dict[str, Any]] = {}

# Session constants
SESSION_TIMEOUT = timedelta(hours=1)
MAX_CONVERSATION_HISTORY = 1
RECENT_EXCHANGES_FOR_CONTEXT = 3
DEFAULT_FRONTEND_INITIAL_ROWS = 30

# Import from centralized constants
from src.common.constants import (
    MAX_CACHE_ROWS,
    PREVIEW_ROWS,
    CACHE_TTL_SECONDS,
    CACHE_CLEANUP_INTERVAL_SECONDS,
    CSV_CHUNK_SIZE,
    LARGE_RESULT_SET_THRESHOLD
)

def get_cache_entry(query_id: str) -> Dict[str, Any]:
    """Get cache entry or raise 404 if not found."""
    if query_id not in query_cache:
        raise HTTPException(status_code=404, detail="Query ID not found")
    return query_cache[query_id]


# ================================
# SESSION MANAGEMENT FUNCTIONS
# ================================

def get_or_create_session(session_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """Get existing session or create new one, cleaning up expired sessions."""
    _cleanup_expired_sessions()

    if session_id and session_id in sessions:
        sessions[session_id]['last_activity'] = datetime.now()
        return session_id, sessions[session_id]

    # Create new session
    new_id = str(uuid.uuid4())
    sessions[new_id] = {
        'created_at': datetime.now(),
        'last_activity': datetime.now(),
        'conversation_history': []
    }
    logger.info(f"Created new session: {new_id}")
    return new_id, sessions[new_id]


def _cleanup_expired_sessions():
    """Remove expired sessions from memory."""
    now = datetime.now()
    expired = [sid for sid, sess in sessions.items()
               if now - sess['last_activity'] > SESSION_TIMEOUT]
    for sid in expired:
        del sessions[sid]
        logger.info(f"Cleaned up expired session: {sid}")


def add_to_conversation(session_id: str, user_message: str, sql: Optional[str]):
    """Add a query to the conversation history, keeping only recent exchanges."""
    if session_id in sessions:
        sessions[session_id]['conversation_history'].append({
            'user_message': user_message,
            'sql': sql,
            'timestamp': datetime.now().isoformat()
        })
        # Keep only last N exchanges to avoid context length issues
        history = sessions[session_id]['conversation_history']
        if len(history) > MAX_CONVERSATION_HISTORY:
            sessions[session_id]['conversation_history'] = history[-MAX_CONVERSATION_HISTORY:]


def build_context_prompt(session: Dict[str, Any], current_message: str) -> str:
    """Build a contextualized prompt with conversation history."""
    history = session.get('conversation_history', [])
    if not history:
        return current_message

    context_parts = ["CONVERSATION HISTORY - Use this to understand follow-up questions:\n"]

    recent_history = history[-RECENT_EXCHANGES_FOR_CONTEXT:]
    for i, exchange in enumerate(recent_history, 1):
        context_parts.append(
            f"Exchange {i}:"
            f"\n  User asked: {exchange['user_message']}"
            f"\n  SQL query: {exchange['sql']}\n"
        )

    context_parts.append(f"USER'S NEW QUESTION: {current_message}")
    context_parts.append(_get_context_rules())

    return "\n".join(context_parts)


def _get_context_rules() -> str:
    """Get the context rules for follow-up questions."""
    return """
CONTEXT RULES FOR FOLLOW-UP QUESTIONS:

When the user's question builds on previous queries, use the conversation history to:

1. Resolve references to entities, tables, or columns mentioned previously
   - "the pool", "those servers", "their names" should reference entities from prior queries

2. Preserve the user's intent when modifying queries
   - "also show X" or "as well" → add columns/joins to previous query while preserving filters
   - "remove X" or "don't show Y" → exclude specified columns from previous SELECT
   - "sort by X instead" → keep same data but change ORDER BY clause

3. Maintain consistency with previous query patterns
   - If previous query returned detail rows, continue returning details unless user requests aggregation
   - If previous query used specific filters (WHERE) or limits, preserve them unless explicitly changed
   - If previous query joined certain tables, reuse those relationships when relevant

Generate SQL that naturally continues the conversation based on the context above."""


# ================================
# CHAT HELPER FUNCTIONS
# ================================

def build_display_info(data: List, total_count: Optional[int]) -> Dict[str, Any]:
    """Build display info for frontend pagination."""
    initial_display = int(os.getenv("FRONTEND_INITIAL_ROWS", str(DEFAULT_FRONTEND_INITIAL_ROWS)))
    return {
        "total_rows": len(data),
        "initial_display": initial_display,
        "has_scroll_data": len(data) > initial_display,
        "total_in_dataset": total_count if total_count is not None else "1000+"
    }


def build_analysis_explanation(interpretation_data: dict, total_count: Optional[int]) -> str:
    """Build markdown-formatted analysis from structured interpretation data."""
    parts = []
    interp = interpretation_data.get("interpretation", {})

    summary = interp.get("summary", "")
    if summary:
        parts.append(f"**Summary:**\n\n{summary}\n\n")

    findings = interp.get("key_findings", [])
    if findings:
        parts.append("**Key Findings:**\n\n")
        for finding in findings:
            parts.append(f"- {finding}\n")
        parts.append("\n")

    recommendations = interp.get("recommendations", [])
    if recommendations:
        parts.append("**Recommendations:**\n\n")
        for recommendation in recommendations:
            parts.append(f"- {recommendation}\n")
        parts.append("\n")

    if total_count and total_count > 30:
        parts.append(f"**Analysis Note:**\n\nInsights based on first 30 rows of {total_count} rows. Download full dataset for complete analysis.\n\n")
    elif total_count is None:
        parts.append("**Analysis Note:**\n\nInsights based on first 30 rows of more than 1000 rows. Download full dataset for complete analysis.\n\n")

    return "".join(parts)


def extract_interpretation_fields(interpretation_data: dict) -> Tuple[Optional[dict], Optional[dict], List[str], bool]:
    """Extract and validate visualization, schema_overview, suggested_queries, and guidance."""
    visualization = interpretation_data.get("visualization")
    schema_overview = interpretation_data.get("schema_overview")
    suggested_queries = interpretation_data.get("suggested_queries") or []
    guidance = interpretation_data.get("guidance", False)

    if not any([schema_overview, suggested_queries]):
        interp_payload = interpretation_data.get("interpretation", {})
        schema_overview = schema_overview or interp_payload.get("schema_overview")
        suggested_queries = suggested_queries or interp_payload.get("suggested_queries") or []
        guidance = guidance or interp_payload.get("guidance", False)

    schema_overview = schema_overview if isinstance(schema_overview, dict) else None
    suggested_queries = suggested_queries if isinstance(suggested_queries, list) else []

    return visualization, schema_overview, suggested_queries, guidance


def build_interpretation_payload(interpretation_data: dict, total_count: Optional[int]) -> dict:
    """Build complete interpretation payload from backend response."""
    analysis_explanation = build_analysis_explanation(interpretation_data, total_count)
    visualization, schema_overview, suggested_queries, _ = extract_interpretation_fields(interpretation_data)

    return {
        'analysis': analysis_explanation,
        'visualization': visualization,
        'schema_overview': schema_overview,
        'suggested_queries': suggested_queries
    }


def yield_sse_event(event_type: str, data: dict) -> str:
    """Helper to format Server-Sent Events consistently."""
    payload = {'type': event_type, **data}
    return f"data: {json.dumps(payload)}\n\n"


# Cleanup task for expired cache entries
async def cleanup_expired_cache():
    """Background task to clean up expired cache entries (both query results and SQL cache)."""
    # Track iterations for less frequent SQL cache pruning
    iteration = 0
    SQL_CACHE_PRUNE_INTERVAL = 288  # Prune SQL cache every 288 iterations (24 hours at 5-min intervals)

    while True:
        try:
            current_time = datetime.now()

            # Clean up in-memory query results cache (every 5 minutes)
            expired_keys = []
            for query_id, cache_entry in query_cache.items():
                if current_time - cache_entry["timestamp"] > timedelta(seconds=CACHE_TTL_SECONDS):
                    expired_keys.append(query_id)

            for key in expired_keys:
                del query_cache[key]
                logger.info(f"Cleaned up expired query result: {key}")

            # Prune SQL cache periodically (every 24 hours)
            iteration += 1
            if iteration % SQL_CACHE_PRUNE_INTERVAL == 0:
                from src.api.app_context import AppContext
                sql_cache = AppContext.get_instance().get_sql_cache()
                deleted = sql_cache.prune_old_entries(days=30)
                if deleted > 0:
                    logger.info(f"Pruned {deleted} old SQL cache entries (runs daily)")

            await asyncio.sleep(CACHE_CLEANUP_INTERVAL_SECONDS)
        except Exception as e:
            logger.error(f"Error in cache cleanup: {e}")
            await asyncio.sleep(CACHE_CLEANUP_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Initializing resources...")

    # Initialize all AppContext resources eagerly
    initialize_app_context()

    # Start cache cleanup task
    cleanup_task = asyncio.create_task(cleanup_expired_cache())

    logger.info("Application ready!")

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Clean up AppContext resources
    cleanup_app_context()

    logger.info("Application shutdown complete")

# ================================
# FASTAPI APP SETUP
# ================================

# Create FastAPI app
app = FastAPI(
    title="Netquery API",
    description="Text-to-SQL API for network infrastructure queries",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for React frontend
# Allow multiple origins from environment variable (comma-separated)
cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
# STATIC FILE SERVING (React build)
# ================================

# Path to React build directory (configurable via environment)
STATIC_DIR = Path(os.getenv("STATIC_DIR", "../netquery-insight-chat/build"))


def setup_static_files():
    """Setup static file serving for React frontend if build directory exists."""
    static_path = STATIC_DIR if STATIC_DIR.is_absolute() else Path(__file__).parent.parent.parent / STATIC_DIR

    if static_path.exists() and (static_path / "index.html").exists():
        logger.info(f"Serving React frontend from: {static_path}")

        # Serve static assets (JS, CSS, images)
        app.mount("/static", StaticFiles(directory=str(static_path / "static")), name="static")

        # Catch-all route for SPA - must be added after API routes
        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            """Serve React SPA for non-API routes."""
            # Don't intercept API routes
            if full_path.startswith("api/") or full_path in ["chat", "health", "schema"]:
                raise HTTPException(status_code=404, detail="Not found")

            # Check if it's a static file
            file_path = static_path / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))

            # Return index.html for SPA routing
            return FileResponse(str(static_path / "index.html"))

        return True
    else:
        logger.info(f"React build not found at {static_path}. API-only mode.")
        return False


# ================================
# PYDANTIC MODELS
# ================================

# Request/Response Models
class GenerateSQLRequest(BaseModel):
    query: str = Field(..., description="Natural language query")

class GenerateSQLResponse(BaseModel):
    query_id: str = Field(..., description="Unique query identifier")
    sql: Optional[str] = Field(None, description="Generated SQL query (null for general questions)")
    original_query: str = Field(..., description="Original natural language query")
    intent: Optional[str] = Field(None, description="Query intent: sql, general, or mixed")
    general_answer: Optional[str] = Field(None, description="Direct answer for general/mixed questions")

class PreviewResponse(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description=f"First {PREVIEW_ROWS} rows of results")
    total_count: Optional[int] = Field(None, description=f"Exact count if ≤{LARGE_RESULT_SET_THRESHOLD} rows, None if >{LARGE_RESULT_SET_THRESHOLD}")
    columns: List[str] = Field(..., description="Column names")
    truncated: bool = Field(..., description=f"Whether preview was truncated to {PREVIEW_ROWS} rows")
    intent: Optional[str] = Field(None, description="Query intent: sql, general, or mixed")
    general_answer: Optional[str] = Field(None, description="Direct answer for general/mixed questions")

class InterpretationData(BaseModel):
    """Structured interpretation with plain text (no markdown) for frontend formatting."""
    summary: str = Field(..., description="Brief summary in plain text")
    key_findings: List[str] = Field(default_factory=list, description="List of key findings in plain text")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations in plain text")

class InterpretationResponse(BaseModel):
    interpretation: InterpretationData = Field(..., description="Structured interpretation data")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Single best chart specification")
    data_truncated: bool = Field(..., description="Whether data was truncated for interpretation")
    analysis: Optional[str] = Field(None, description="Formatted markdown analysis text")


class SchemaOverviewTable(BaseModel):
    name: str
    description: str
    key_columns: List[str] = Field(default_factory=list)
    columns: List[Dict[str, str]] = Field(default_factory=list)
    related_tables: List[str] = Field(default_factory=list)
    relationships: List[Dict[str, str]] = Field(default_factory=list)


class SchemaOverviewResponse(BaseModel):
    schema_id: Optional[str]
    tables: List[SchemaOverviewTable]
    suggested_queries: List[str]


# Chat endpoint models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    include_interpretation: bool = False


class FeedbackRequest(BaseModel):
    type: str  # 'thumbs_up' or 'thumbs_down'
    query_id: Optional[str] = None
    user_question: Optional[str] = None
    sql_query: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    timestamp: str


# ================================
# API ENDPOINTS
# ================================


@app.get("/api/schema/overview", response_model=SchemaOverviewResponse)
async def schema_overview(database: Optional[str] = None) -> SchemaOverviewResponse:
    """
    Return a high-level overview of available tables and sample prompts.

    In multi-database mode (dual backends): uses frontend's database parameter
    In single-database mode (production): always uses backend's SCHEMA_ID
    """
    # Check if multi-database mode is enabled (dual backends)
    multi_db_mode = os.getenv("MULTI_DATABASE_MODE", "false").lower() == "true"

    if multi_db_mode and database:
        schema_id = database
    else:
        schema_id = os.getenv("SCHEMA_ID")

    overview = get_schema_overview(database=schema_id)
    tables = overview.get("tables", [])
    if not tables:
        detail = overview.get("error") or {
            "message": "Schema overview not available",
            "environment": os.getenv("NETQUERY_ENV", "dev")
        }
        raise HTTPException(status_code=404, detail=detail)

    return SchemaOverviewResponse(
        schema_id=overview.get("schema_id"),
        tables=[SchemaOverviewTable(**table) for table in tables],
        suggested_queries=overview.get("suggested_queries", [])
    )


@app.post("/api/generate-sql", response_model=GenerateSQLResponse)
async def generate_sql_endpoint(request: GenerateSQLRequest) -> GenerateSQLResponse:
    """
    Generate SQL from natural language query without execution.
    """
    from .services.sql_service import generate_sql

    query_id = str(uuid.uuid4())

    result = await generate_sql(
        query=request.query,
        text_to_sql_graph=text_to_sql_graph,
        get_schema_overview_fn=get_schema_overview
    )

    # Handle general questions (no SQL needed)
    if result.intent == "general":
        return GenerateSQLResponse(
            query_id=query_id,
            sql=None,
            original_query=request.query,
            intent="general",
            general_answer=result.general_answer
        )

    # Handle generation failure
    if result.error:
        overview = result.schema_overview or get_schema_overview()
        raise HTTPException(status_code=422, detail={
            "message": result.error,
            "type": "generation_error",
            "schema_overview": overview,
            "suggested_queries": overview.get("suggested_queries", []) if overview else []
        })

    # Store in cache
    query_cache[query_id] = {
        "sql": result.sql,
        "original_query": request.query,
        "intent": result.intent,
        "general_answer": result.general_answer,
        "data": None,
        "total_count": None,
        "timestamp": datetime.now()
    }

    return GenerateSQLResponse(
        query_id=query_id,
        sql=result.sql,
        original_query=request.query,
        intent=result.intent or "sql",
        general_answer=result.general_answer
    )

@app.get("/api/execute/{query_id}", response_model=PreviewResponse)
async def execute_and_preview(query_id: str) -> PreviewResponse:
    """
    Execute SQL query, cache results, and return preview.
    - Executes the SQL query from the cache
    - Fetches up to MAX_CACHE_ROWS rows and caches them
    - Returns first PREVIEW_ROWS rows for preview
    """
    from .services.execution_service import execute_sql

    # Check cache
    cache_entry = get_cache_entry(query_id)

    # If data already cached, return it
    if cache_entry["data"] is not None:
        data = cache_entry["data"]
        return PreviewResponse(
            data=data[:PREVIEW_ROWS],
            total_count=cache_entry["total_count"],
            columns=list(data[0].keys()) if data else [],
            truncated=len(data) > PREVIEW_ROWS,
            intent=cache_entry.get("intent"),
            general_answer=cache_entry.get("general_answer")
        )

    # Execute the query using service
    result = execute_sql(
        sql=cache_entry["sql"],
        engine=get_engine(),
        max_rows=MAX_CACHE_ROWS,
        count_threshold=LARGE_RESULT_SET_THRESHOLD
    )

    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    # Update cache
    cache_entry["data"] = result.data
    cache_entry["total_count"] = result.total_count
    cache_entry["timestamp"] = datetime.now()

    return PreviewResponse(
        data=result.data[:PREVIEW_ROWS],
        total_count=result.total_count,
        columns=result.columns,
        truncated=len(result.data) > PREVIEW_ROWS,
        intent=cache_entry.get("intent"),
        general_answer=cache_entry.get("general_answer")
    )

@app.get("/api/interpret/{query_id}", response_model=InterpretationResponse)
async def interpret_results(query_id: str) -> InterpretationResponse:
    """
    Interpret cached results with FAST visualization + async LLM interpretation.

    PERFORMANCE OPTIMIZED:
    - Visualization: Selected locally (0ms, no LLM) using pre-computed patterns
    - Interpretation: LLM-powered insights (async, runs in background)
    - Users see visualization INSTANTLY, interpretation arrives when ready

    IMPORTANT: Uses ONLY the MAX_CACHE_ROWS cached rows - does NOT re-execute SQL.
    """
    try:
        # Check cache
        cache_entry = get_cache_entry(query_id)

        # Ensure data is cached
        if cache_entry["data"] is None:
            raise HTTPException(
                status_code=400,
                detail="No data cached. Please call /execute first."
            )

        data = cache_entry["data"]
        total_count = cache_entry.get("total_count")
        query = cache_entry["original_query"]
        general_answer = cache_entry.get("general_answer")

        # STEP 1: INSTANT visualization selection (no LLM, 0ms)
        from src.api.services.interpretation_service import get_visualization_for_data

        visualization = get_visualization_for_data(query, data)

        # STEP 2: LLM interpretation (runs async, slower but higher quality)
        # For mixed queries, this will prepend the general answer
        from src.api.services.interpretation_service import get_interpretation_only

        interpretation = await get_interpretation_only(
            query=query,
            results=data,  # All cached data (≤MAX_CACHE_ROWS rows)
            total_rows=total_count,
            general_answer=general_answer
        )

        # Data is truncated if total_count is None (>1000 rows) OR total_count > cache size
        data_truncated = total_count is None or (total_count and total_count > MAX_CACHE_ROWS)

        # Build formatted analysis text for frontend
        analysis_text = build_analysis_explanation({"interpretation": interpretation}, total_count)

        return InterpretationResponse(
            interpretation=interpretation,
            visualization=visualization,
            data_truncated=data_truncated,
            analysis=analysis_text
        )

    except Exception as e:
        logger.error(f"Error interpreting results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{query_id}")
async def download_csv(query_id: str):
    """
    Download full results as CSV (streams all rows).
    """
    try:
        # Check cache
        cache_entry = get_cache_entry(query_id)
        sql = cache_entry["sql"]

        # Stream the results as CSV
        def generate_csv():
            import pandas as pd  # Lazy import - only needed for CSV export

            engine = get_engine()
            with engine.connect() as conn:
                # Use pandas to read SQL in chunks and write to CSV
                first_chunk = True

                for chunk_df in pd.read_sql(sql, conn, chunksize=CSV_CHUNK_SIZE):
                    # Convert chunk to CSV
                    csv_buffer = StringIO()
                    chunk_df.to_csv(csv_buffer, index=False, header=first_chunk)
                    yield csv_buffer.getvalue()
                    first_chunk = False

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_results_{query_id[:8]}_{timestamp}.csv"

        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Error downloading CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# CHAT ENDPOINTS
# ================================

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint - Orchestrates the full chat workflow via SSE streaming.

    This combines session management, SQL generation, execution, and interpretation
    into a single streaming response.
    """

    async def event_generator():
        from .services.sql_service import generate_sql
        from .services.execution_service import execute_sql

        try:
            # Get or create session
            session_id, session = get_or_create_session(request.session_id)
            logger.info(f"Processing streaming query (session: {session_id}): {request.message[:80]}...")

            # Send session ID immediately
            yield yield_sse_event('session', {'session_id': session_id})

            # Build context-aware message if we have conversation history
            contextualized_message = request.message
            if session and session.get('conversation_history'):
                contextualized_message = build_context_prompt(session, request.message)

            # Step 1: Generate SQL (or get general answer)
            query_id = str(uuid.uuid4())

            gen_result = await generate_sql(
                query=contextualized_message,
                text_to_sql_graph=text_to_sql_graph,
                get_schema_overview_fn=get_schema_overview
            )

            # Handle generation failure
            if gen_result.error and gen_result.intent != "general":
                overview = gen_result.schema_overview or get_schema_overview()
                guidance_payload = {
                    "message": gen_result.error,
                    "schema_overview": overview,
                    "suggested_queries": overview.get("suggested_queries", []) if overview else []
                }
                yield yield_sse_event('guidance', guidance_payload)
                yield yield_sse_event('done', {})
                return

            generated_sql = gen_result.sql
            intent = gen_result.intent
            general_answer = gen_result.general_answer

            # Handle based on intent type
            if intent == "general":
                logger.info(f"General question detected: {request.message[:80]}...")
                yield yield_sse_event('general_answer', {
                    'answer': general_answer,
                    'query_id': query_id
                })
                add_to_conversation(session_id, request.message, None)
                yield yield_sse_event('done', {})
                return

            # For SQL and mixed intents, we need to execute SQL
            if intent == "mixed" and general_answer:
                yield yield_sse_event('general_answer', {
                    'answer': general_answer,
                    'query_id': query_id
                })

            # Store in cache for execution
            query_cache[query_id] = {
                "sql": generated_sql,
                "original_query": request.message,
                "intent": intent,
                "general_answer": general_answer,
                "data": None,
                "total_count": None,
                "timestamp": datetime.now()
            }

            # Send SQL
            sql_explanation = f"**SQL Query:**\n```sql\n{generated_sql}\n```\n\n"
            yield yield_sse_event('sql', {
                'sql': generated_sql,
                'query_id': query_id,
                'explanation': sql_explanation,
                'intent': intent
            })

            # Step 2: Execute and get data
            exec_result = execute_sql(
                sql=generated_sql,
                engine=get_engine(),
                max_rows=MAX_CACHE_ROWS,
                count_threshold=LARGE_RESULT_SET_THRESHOLD
            )

            if exec_result.error:
                logger.error(f"Query execution error: {exec_result.error}")
                yield yield_sse_event('error', {'message': f"Query execution failed: {exec_result.error}"})
                return

            data = exec_result.data
            total_count = exec_result.total_count

            # Update cache
            query_cache[query_id]["data"] = data
            query_cache[query_id]["total_count"] = total_count

            # Send data
            display_info = build_display_info(data, total_count)
            yield yield_sse_event('data', {
                'results': data,
                'display_info': display_info
            })

            # Step 3: Get interpretation (only if requested)
            if request.include_interpretation:
                try:
                    from src.api.services.interpretation_service import get_visualization_for_data, get_interpretation_only

                    visualization = get_visualization_for_data(request.message, data)

                    interpretation = await get_interpretation_only(
                        query=request.message,
                        results=data,
                        total_rows=total_count,
                        general_answer=general_answer
                    )

                    interpretation_payload = {
                        'analysis': build_analysis_explanation({"interpretation": interpretation}, total_count),
                        'visualization': visualization,
                        'schema_overview': None,
                        'suggested_queries': []
                    }

                    yield yield_sse_event('interpretation', interpretation_payload)

                except Exception as interp_error:
                    logger.error(f"Interpretation error: {interp_error}")
                    # Non-fatal, continue

            # Add to conversation history
            add_to_conversation(session_id, request.message, generated_sql)

            # Send completion signal
            yield yield_sse_event('done', {})

        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            yield yield_sse_event('error', {'message': str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Feedback file path (configurable via environment)
FEEDBACK_FILE = Path(os.getenv("FEEDBACK_FILE", "data/feedback.jsonl"))


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    User feedback endpoint - Collects thumbs up/down feedback from chat UI.
    """
    try:
        # Resolve feedback file path relative to project root
        feedback_path = FEEDBACK_FILE if FEEDBACK_FILE.is_absolute() else Path(__file__).parent.parent.parent / FEEDBACK_FILE

        # Ensure parent directory exists
        feedback_path.parent.mkdir(parents=True, exist_ok=True)

        feedback_data = {
            "type": request.type,
            "query_id": request.query_id,
            "user_question": request.user_question,
            "sql_query": request.sql_query,
            "description": request.description,
            "tags": request.tags,
            "timestamp": request.timestamp
        }

        with open(feedback_path, "a") as f:
            f.write(json.dumps(feedback_data) + "\n")

        logger.info(f"Feedback saved: {request.type} for query_id: {request.query_id}")

        return {"status": "success", "message": "Feedback submitted successfully"}

    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "cache_size": len(query_cache), "session_count": len(sessions)}


# Setup static file serving (must be after all API routes are defined)
# This adds the catch-all route for React SPA
setup_static_files()


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="NetQuery API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    schema_id = os.getenv('SCHEMA_ID', 'not set')
    database_url = os.getenv('DATABASE_URL', 'not set')
    logger.info(f"Starting NetQuery API server on {args.host}:{args.port}")
    logger.info(f"Environment: {schema_id} database ({database_url})")

    # Use import string for reload support
    uvicorn.run(
        "src.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=["src"] if args.reload else None,  # Only watch src/ directory
    )
