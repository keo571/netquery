"""
State definition for the Text-to-SQL pipeline.
"""
from typing import TypedDict, List, Dict, Any, Optional, TYPE_CHECKING
from typing_extensions import Annotated
import operator

if TYPE_CHECKING:
    from src.schema_ingestion.canonical import CanonicalSchema


class ReasoningStep(TypedDict):
    """A step in the pipeline's reasoning process."""
    step_name: str
    details: str
    status: str  # "✅", "⚠️", "❌"


class TextToSQLState(TypedDict):
    """State for the Text-to-SQL pipeline workflow."""

    # Core Input/Output
    original_query: str
    generated_sql: str
    query_results: Optional[List[Dict]]
    final_response: str
    formatted_response: str
    show_explanation: bool
    export_csv: Optional[bool]
    export_html: Optional[bool]
    execute: Optional[bool]  # Whether to execute the SQL query

    # Schema Input
    canonical_schema_path: Optional[str]  # Path to canonical schema JSON
    canonical_schema: Optional[Any]  # Loaded CanonicalSchema object (use Any to avoid TypedDict issues)

    # Schema Analysis
    schema_context: str
    schema_analysis_error: Optional[str]
    
    # Query Planning
    query_plan: Dict[str, Any]
    complexity_assessment: str
    planning_error: Optional[str]
    
    # Generation & Validation
    generation_error: Optional[str]
    validation_results: Dict[str, Any]
    safety_checks: Dict[str, bool]
    is_valid: bool
    validation_error: Optional[str]
    
    # Execution
    execution_time_ms: Optional[float]
    total_pipeline_time_ms: Optional[float]
    schema_analysis_time_ms: Optional[float]
    query_planning_time_ms: Optional[float]
    sql_generation_time_ms: Optional[float]
    interpretation_time_ms: Optional[float]
    rows_affected: Optional[int]
    execution_error: Optional[str]
    
    # CSV export path
    csv_export_path: Optional[str]
    
    # Chart HTML for visualization
    chart_html: Optional[str]
    
    # Reasoning Log
    reasoning_log: Annotated[List[ReasoningStep], operator.add]


class QueryPlan(TypedDict):
    """Query planning information."""
    intent: str
    target_tables: List[str]
    required_columns: List[str]
    filters: List[Dict[str, Any]]
    aggregations: List[Dict[str, Any]]
    sorting: Optional[Dict[str, str]]
    grouping: Optional[List[str]]
    joins: List[Dict[str, Any]]
    estimated_complexity: str


class ValidationResult(TypedDict):
    """SQL validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    allowed_tables: List[str]