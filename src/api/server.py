"""
FastAPI server for Netquery Text-to-SQL system.
"""

# ================================
# IMPORTS
# ================================

import uuid
import logging
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import pandas as pd
from io import StringIO
from sqlalchemy import text
from src.common.env import load_environment
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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

# ================================
# API ENDPOINTS
# ================================


@app.get("/api/schema/overview", response_model=SchemaOverviewResponse)
async def schema_overview(database: Optional[str] = None) -> SchemaOverviewResponse:
    """
    Return a high-level overview of available tables and sample prompts.

    Args:
        database: Database name (e.g., 'sample', 'neila') - defaults to current backend's schema
    """
    # If no database specified, use the current backend's schema ID
    if database is None:
        database = os.getenv("SCHEMA_ID")
    overview = get_schema_overview(database=database)
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
async def generate_sql(request: GenerateSQLRequest) -> GenerateSQLResponse:
    """
    Generate SQL from natural language query without execution.
    """
    try:
        query_id = str(uuid.uuid4())

        # Use the pipeline with execute=False
        result = await text_to_sql_graph.ainvoke({
            "original_query": request.query,
            "execute": False,  # Don't execute the SQL
            "show_explanation": False
        })

        generated_sql = result.get("generated_sql")

        intent = result.get("intent")
        general_answer = result.get("general_answer")

        if not generated_sql:
            # Check if this was a general question (not needing SQL)
            if intent == "general":
                # Return the direct answer for general questions
                return GenerateSQLResponse(
                    query_id=query_id,
                    sql=None,
                    original_query=request.query,
                    intent="general",
                    general_answer=general_answer or result.get("final_response")
                )
            else:
                # Regular SQL generation failure
                overview = result.get("schema_overview") or get_schema_overview()
                detail_payload = {
                    "message": result.get("final_response") or "Failed to generate SQL",
                    "type": "generation_error",
                    "schema_overview": overview,
                    "suggested_queries": overview.get("suggested_queries", []) if overview else [],
                    "schema_analysis_error": result.get("schema_analysis_error"),
                    "generation_error": result.get("generation_error"),
                }
            raise HTTPException(status_code=422, detail=detail_payload)

        # Store in cache
        query_cache[query_id] = {
            "sql": generated_sql,
            "original_query": request.query,
            "intent": intent,
            "general_answer": general_answer,
            "data": None,  # No data yet
            "total_count": None,
            "timestamp": datetime.now()
        }

        return GenerateSQLResponse(
            query_id=query_id,
            sql=generated_sql,
            original_query=request.query,
            intent=intent or "sql",  # Default to "sql" if not set
            general_answer=general_answer  # Will be None for pure SQL, set for mixed
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/execute/{query_id}", response_model=PreviewResponse)
async def execute_and_preview(query_id: str) -> PreviewResponse:
    """
    Execute SQL query, cache results, and return preview.
    - Executes the SQL query from the cache
    - Fetches up to MAX_CACHE_ROWS rows and caches them
    - Returns first PREVIEW_ROWS rows for preview
    """
    try:
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

        # Execute the query
        sql = cache_entry["sql"]
        # Remove trailing semicolon if present (causes issues in subqueries)
        sql = sql.rstrip(';')
        engine = get_engine()

        # Check if there's more data than LARGE_RESULT_SET_THRESHOLD rows for counting
        # This is MUCH faster than counting all rows
        check_more_sql = f"SELECT 1 FROM ({sql}) as sq LIMIT {LARGE_RESULT_SET_THRESHOLD + 1}"
        with engine.connect() as conn:
            check_results = conn.execute(text(check_more_sql)).fetchall()
            has_more_than_threshold = len(check_results) > LARGE_RESULT_SET_THRESHOLD

            # Set total_count based on LARGE_RESULT_SET_THRESHOLD
            if has_more_than_threshold:
                total_count = None  # We don't know the exact count (>threshold)
            else:
                total_count = len(check_results)  # Exact count ≤threshold

        # Fetch up to MAX_CACHE_ROWS rows for actual data
        # Check if SQL already has a LIMIT clause
        if 'LIMIT' in sql.upper():
            # Use the existing SQL as-is if it has LIMIT
            limited_sql = sql
        else:
            limited_sql = f"{sql} LIMIT {MAX_CACHE_ROWS}"
        with engine.connect() as conn:
            result = conn.execute(text(limited_sql))
            rows = result.fetchall()
            columns = list(result.keys())

        # Convert to list of dicts
        data = [dict(zip(columns, row)) for row in rows]

        # Format data for better display (import the function)
        from .services.data_utils import format_data_for_display
        data = format_data_for_display(data)

        # Update cache
        cache_entry["data"] = data
        cache_entry["total_count"] = total_count
        cache_entry["timestamp"] = datetime.now()

        return PreviewResponse(
            data=data[:PREVIEW_ROWS],
            total_count=total_count,
            columns=columns,
            truncated=len(data) > PREVIEW_ROWS,
            intent=cache_entry.get("intent"),
            general_answer=cache_entry.get("general_answer")
        )

    except Exception as e:
        logger.error(f"Error previewing results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interpret/{query_id}", response_model=InterpretationResponse)
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
        from src.api.services.interpretation_service import select_visualization_fast, process_visualization_data
        from src.api.services.data_utils import analyze_data_patterns

        patterns = analyze_data_patterns(data) if data else {}
        visualization = select_visualization_fast(query, data, patterns)

        # Process visualization data (e.g., perform grouping/aggregation if needed)
        visualization = process_visualization_data(visualization, data)

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

        return InterpretationResponse(
            interpretation=interpretation,
            visualization=visualization,
            data_truncated=data_truncated
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

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "cache_size": len(query_cache)}

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
