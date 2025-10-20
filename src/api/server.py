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

import pandas as pd  # Only used for CSV download
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
from src.api.services import get_interpretation

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
CACHE_TTL = 600  # 10 minutes default
MAX_CACHE_ROWS = 100
PREVIEW_ROWS = 100  # Return all cached rows - client can paginate if needed

def get_cache_entry(query_id: str) -> Dict[str, Any]:
    """Get cache entry or raise 404 if not found."""
    if query_id not in query_cache:
        raise HTTPException(status_code=404, detail="Query ID not found")
    return query_cache[query_id]

# Cleanup task for expired cache entries
async def cleanup_expired_cache():
    """Background task to clean up expired cache entries."""
    while True:
        try:
            current_time = datetime.now()
            expired_keys = []

            for query_id, cache_entry in query_cache.items():
                if current_time - cache_entry["timestamp"] > timedelta(seconds=CACHE_TTL):
                    expired_keys.append(query_id)

            for key in expired_keys:
                del query_cache[key]
                logger.info(f"Cleaned up expired cache entry: {key}")

            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error in cache cleanup: {e}")
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    cleanup_task = asyncio.create_task(cleanup_expired_cache())
    yield
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
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
    sql: str = Field(..., description="Generated SQL query")
    original_query: str = Field(..., description="Original natural language query")

class PreviewResponse(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="First 30 rows of results")
    total_count: Optional[int] = Field(None, description="Exact count if ≤1000 rows, None if >1000")
    columns: List[str] = Field(..., description="Column names")
    truncated: bool = Field(..., description="Whether preview was truncated to 30 rows")

class InterpretationResponse(BaseModel):
    interpretation: Dict[str, Any] = Field(..., description="Interpretation results")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Single best chart specification")
    data_truncated: bool = Field(..., description="Whether data was truncated for interpretation")


class SchemaOverviewTable(BaseModel):
    name: str
    description: str
    key_columns: List[str] = Field(default_factory=list)
    related_tables: List[str] = Field(default_factory=list)


class SchemaOverviewResponse(BaseModel):
    schema_id: Optional[str]
    tables: List[SchemaOverviewTable]
    suggested_queries: List[str]

# ================================
# API ENDPOINTS
# ================================


@app.get("/api/schema/overview", response_model=SchemaOverviewResponse)
async def schema_overview() -> SchemaOverviewResponse:
    """Return a high-level overview of available tables and sample prompts."""
    overview = get_schema_overview()
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

        if not generated_sql:
            overview = result.get("schema_overview") or get_schema_overview()
            detail_payload = {
                "message": result.get("final_response") or "Failed to generate SQL",
                "schema_overview": overview,
                "schema_analysis_error": result.get("schema_analysis_error"),
                "generation_error": result.get("generation_error"),
            }
            raise HTTPException(status_code=422, detail=detail_payload)

        # Store in cache
        query_cache[query_id] = {
            "sql": generated_sql,
            "original_query": request.query,
            "data": None,  # No data yet
            "total_count": None,
            "timestamp": datetime.now()
        }

        return GenerateSQLResponse(
            query_id=query_id,
            sql=generated_sql,
            original_query=request.query
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
    - Fetches up to 1000 rows and caches them
    - Returns first 30 rows for preview
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
                truncated=len(data) > PREVIEW_ROWS
            )

        # Execute the query
        sql = cache_entry["sql"]
        # Remove trailing semicolon if present (causes issues in subqueries)
        sql = sql.rstrip(';')
        engine = get_engine()

        # Check if there's more data than 1000 rows for counting
        # This is MUCH faster than counting all rows
        count_limit = 1000
        check_more_sql = f"SELECT 1 FROM ({sql}) as sq LIMIT {count_limit + 1}"
        with engine.connect() as conn:
            check_results = conn.execute(text(check_more_sql)).fetchall()
            has_more_than_count_limit = len(check_results) > count_limit

            # Set total_count based on 1000 row limit
            if has_more_than_count_limit:
                total_count = None  # We don't know the exact count (>1000)
            else:
                total_count = len(check_results)  # Exact count ≤1000

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
        from .data_utils import format_data_for_display
        data = format_data_for_display(data)

        # Update cache
        cache_entry["data"] = data
        cache_entry["total_count"] = total_count
        cache_entry["timestamp"] = datetime.now()

        return PreviewResponse(
            data=data[:PREVIEW_ROWS],
            total_count=total_count,
            columns=columns,
            truncated=len(data) > PREVIEW_ROWS
        )

    except Exception as e:
        logger.error(f"Error previewing results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interpret/{query_id}", response_model=InterpretationResponse)
async def interpret_results(query_id: str) -> InterpretationResponse:
    """
    Interpret cached results using LLM.
    Uses up to 1000 cached rows for interpretation.
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

        # Get LLM-powered interpretation
        interpretation_result = await get_interpretation(
            query=cache_entry["original_query"],
            results=data,  # All cached data (≤100 rows)
            total_rows=total_count
        )

        # No need to add warning here - frontend will handle based on data_truncated flag

        # Data is truncated if total_count is None (>1000 rows) OR total_count > cache size
        data_truncated = total_count is None or (total_count and total_count > MAX_CACHE_ROWS)

        return InterpretationResponse(
            interpretation=interpretation_result["interpretation"],
            visualization=interpretation_result["visualization"],
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
            engine = get_engine()
            with engine.connect() as conn:
                # Use pandas to read SQL in chunks and write to CSV
                chunk_size = 1000
                first_chunk = True

                for chunk_df in pd.read_sql(sql, conn, chunksize=chunk_size):
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
