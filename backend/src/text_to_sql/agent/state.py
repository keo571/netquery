"""
State definition for the Text-to-SQL agent.
Based on the manager architecture patterns.
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from typing_extensions import Annotated
from langgraph.graph import add_messages
import operator


class ReasoningStep(TypedDict):
    """A dictionary representing a single step in the agent's reasoning process."""
    step_name: str
    summary: str
    outcome: Literal["success", "failure"]


class TextToSQLState(TypedDict):
    """State for the Text-to-SQL agent workflow."""
    
    # Input/Output
    messages: Annotated[list, add_messages]
    original_query: str
    natural_language_query: str
    run_config: Dict[str, Any]
    
    # Schema Analysis
    relevant_tables: List[str]
    schema_context: str  # Formatted schema for LLM
    table_relationships: Dict[str, List[str]]
    
    # Query Planning
    query_plan: Dict[str, Any]
    complexity_assessment: str  # "simple", "medium", "complex"
    requires_joins: bool
    estimated_result_size: Optional[int]
    
    # SQL Generation
    generated_sql: str
    sql_explanation: str
    confidence_score: float
    
    # Validation
    validation_results: Dict[str, Any]
    safety_checks: Dict[str, bool]
    is_valid: bool
    validation_errors: Annotated[List[str], operator.add]
    
    # Execution
    query_results: Optional[List[Dict]]
    execution_time_ms: Optional[float]
    rows_affected: Optional[int]
    execution_error: Optional[str]
    
    # Response
    formatted_response: str
    final_response: str
    include_reasoning: bool
    response_metadata: Dict[str, Any]
    
    # NEW: A log to store the multi-step reasoning process
    reasoning_log: Annotated[List[ReasoningStep], operator.add]


class QueryPlan(TypedDict):
    """Detailed query planning information."""
    intent: str  # "select", "aggregate", "join", "filter", etc.
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
    safety_score: float
    blocked_operations: List[str]
    allowed_tables: List[str]
    syntax_valid: bool


class ExecutionResult(TypedDict):
    """SQL execution result."""
    success: bool
    data: Optional[List[Dict]]
    row_count: int
    execution_time_ms: float
    query_plan: Optional[str]
    error_message: Optional[str]
    warnings: List[str]


class SchemaInfo(TypedDict):
    """Schema information for tables."""
    table_name: str
    columns: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    row_count: Optional[int]
    sample_data: Optional[List[Dict]]
    relationships: Dict[str, List[str]]