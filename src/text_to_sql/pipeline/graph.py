"""
Text-to-SQL pipeline graph implementation.
Uses LangGraph to orchestrate the five-node processing pipeline.
"""
from langgraph.graph import StateGraph, START, END
import logging

from .state import TextToSQLState
from .nodes.triage import triage_node
from .nodes.schema_analyzer import schema_analyzer
from .nodes.sql_generator import sql_generator
from .nodes.validator import validator
from .nodes.executor import executor
from .nodes.interpreter import interpreter

logger = logging.getLogger(__name__)



def error_handler_node(state: TextToSQLState) -> dict:
    """Handle pipeline errors with user-friendly messages."""
    # Check if this is a triage rejection - if so, return as-is (no duplication)
    if state.get("triage_passed") is False:
        # Triage already set final_response, schema_overview, and execution_error
        return {
            "final_response": state.get("final_response"),
            "execution_error": state.get("execution_error"),
            "schema_overview": state.get("schema_overview")
        }

    # Handle other error types
    if state.get("schema_analysis_error"):
        error = state["schema_analysis_error"]
        msg = "I couldn't find relevant database tables for your query."
        hint = "Try asking about specific tables or use different keywords."
    elif state.get("generation_error"):
        error = state["generation_error"]
        msg = "I couldn't generate SQL for your query."
        hint = "Try simplifying your request."
    elif state.get("execution_error"):
        error = state["execution_error"]
        msg = "I couldn't execute the SQL query against the database."
        hint = "This might be a database connectivity issue. Please try again."
    elif not state.get("is_valid", True):
        error = state.get("validation_error", "Validation failed")
        msg = "The SQL query has safety issues."
        hint = "Try breaking your request into simpler parts."
    else:
        error = "Unknown error"
        msg = "Something went wrong processing your query."
        hint = "Please try again."

    # Don't add tables/queries to message text - frontend will display schema_overview separately
    return {
        "final_response": f"{msg}\n\n{hint}",
        "execution_error": error,
        "schema_overview": state.get("schema_overview")
    }

def route_after_triage(state: TextToSQLState) -> str:
    """Route after triage: to schema_analyzer or error handler."""
    return "schema_analyzer" if state.get("triage_passed") else "error_handler"

def route_after_schema(state: TextToSQLState) -> str:
    """Route after schema analysis: directly to sql_generator or error handler."""
    return "error_handler" if state.get("schema_analysis_error") else "sql_generator"

def route_after_generator(state: TextToSQLState) -> str:
    """Route after SQL generation: to validator or error handler."""
    return "error_handler" if state.get("generation_error") else "validator"

def route_after_validator(state: TextToSQLState) -> str:
    """Route after validation: to executor, end (if execute=False), or error handler."""
    if state.get("validation_error"):
        return "error_handler"
    # If execute is False, skip execution and interpretation
    if state.get("execute") is False:
        return "end"
    return "executor"

def route_after_executor(state: TextToSQLState) -> str:
    """Route after execution: to interpreter or error handler."""
    return "error_handler" if state.get("execution_error") else "interpreter"

def create_text_to_sql_graph():
    """Create and compile the Text-to-SQL pipeline graph."""
    # Create the workflow
    workflow = StateGraph(TextToSQLState)

    # Add all pipeline nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("schema_analyzer", schema_analyzer)
    workflow.add_node("sql_generator", sql_generator)
    workflow.add_node("validator", validator)
    workflow.add_node("executor", executor)
    workflow.add_node("interpreter", interpreter)
    workflow.add_node("error_handler", error_handler_node)

    # Add edges - start with triage node
    workflow.add_edge(START, "triage")

    # Route from triage to schema analyzer or error handler
    workflow.add_conditional_edges("triage", route_after_triage,
                                  {"schema_analyzer": "schema_analyzer", "error_handler": "error_handler"})

    # Add conditional routing with error handling
    # Schema analyzer routes directly to SQL generator (no query planner)
    workflow.add_conditional_edges("schema_analyzer", route_after_schema,
                                  {"sql_generator": "sql_generator", "error_handler": "error_handler"})
    workflow.add_conditional_edges("sql_generator", route_after_generator,
                                  {"validator": "validator", "error_handler": "error_handler"})
    # Special routing for validator - can go to executor, end, or error_handler
    workflow.add_conditional_edges(
        "validator",
        route_after_validator,
        {"executor": "executor", "end": END, "error_handler": "error_handler"}
    )
    workflow.add_conditional_edges("executor", route_after_executor,
                                  {"interpreter": "interpreter", "error_handler": "error_handler"})

    # Terminal edges
    workflow.add_edge("interpreter", END)
    workflow.add_edge("error_handler", END)

    # Compile and return the graph
    return workflow.compile()

# Create the compiled graph
text_to_sql_graph = create_text_to_sql_graph()
