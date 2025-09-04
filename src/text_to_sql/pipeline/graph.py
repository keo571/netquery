"""
Text-to-SQL pipeline graph implementation.
Uses existing node implementations from the nodes directory.
"""
from langgraph.graph import StateGraph, START, END
import logging

from .state import TextToSQLState
from .nodes.schema_analyzer import schema_analyzer_node
from .nodes.query_planner import query_planner_node  
from .nodes.sql_generator import sql_generator_node
from .nodes.validator import validator_node
from .nodes.executor import executor_node
from .nodes.interpreter import interpreter_node

logger = logging.getLogger(__name__)


def error_handler_node(state: TextToSQLState) -> dict:
    """Handle pipeline errors with user-friendly messages."""
    # Determine error type and message
    if state.get("schema_analysis_error"):
        error = state["schema_analysis_error"]
        msg = "I couldn't find relevant database tables for your query."
        hint = "Try asking about specific tables or use different keywords."
    elif state.get("planning_error"):
        error = state["planning_error"]
        msg = "I had trouble understanding your query."
        hint = "Try rephrasing or being more specific."
    elif state.get("generation_error"):
        error = state["generation_error"]
        msg = "I couldn't generate SQL for your query."
        hint = "Try simplifying your request."
    elif not state.get("is_valid", True):
        error = state.get("validation_error", "Validation failed")
        msg = "The SQL query has safety issues."
        hint = "Try breaking your request into simpler parts."
    else:
        error = "Unknown error"
        msg = "Something went wrong processing your query."
        hint = "Please try again."
    
    return {
        "final_response": f"{msg}\n\n{hint}",
        "execution_error": error
    }

def route_after_schema(state: TextToSQLState):
    return "error_handler" if state.get("schema_analysis_error") else "query_planner"

def route_after_planner(state: TextToSQLState):
    return "error_handler" if state.get("planning_error") else "sql_generator"

def route_after_generator(state: TextToSQLState):
    return "error_handler" if state.get("generation_error") else "validator"

def route_after_validator(state: TextToSQLState):
    return "error_handler" if state.get("validation_error") else "executor"

def _create_routing_map(next_node: str):
    """Create routing map for conditional edges."""
    return {next_node: next_node, "error_handler": "error_handler"}

# Create the workflow
text_to_sql_workflow = StateGraph(TextToSQLState)

# Add all nodes
text_to_sql_workflow.add_node("schema_analyzer", schema_analyzer_node)
text_to_sql_workflow.add_node("query_planner", query_planner_node)
text_to_sql_workflow.add_node("sql_generator", sql_generator_node)
text_to_sql_workflow.add_node("validator", validator_node)
text_to_sql_workflow.add_node("executor", executor_node)
text_to_sql_workflow.add_node("interpreter", interpreter_node)
text_to_sql_workflow.add_node("error_handler", error_handler_node)

# Add edges
text_to_sql_workflow.add_edge(START, "schema_analyzer")

# Add conditional routing with error handling  
text_to_sql_workflow.add_conditional_edges("schema_analyzer", route_after_schema, _create_routing_map("query_planner"))
text_to_sql_workflow.add_conditional_edges("query_planner", route_after_planner, _create_routing_map("sql_generator"))
text_to_sql_workflow.add_conditional_edges("sql_generator", route_after_generator, _create_routing_map("validator"))
text_to_sql_workflow.add_conditional_edges("validator", route_after_validator, _create_routing_map("executor"))

def route_after_executor(state: TextToSQLState):
    return "error_handler" if state.get("execution_error") else "interpreter"

text_to_sql_workflow.add_conditional_edges("executor", route_after_executor, {"interpreter": "interpreter", "error_handler": "error_handler"})
text_to_sql_workflow.add_edge("interpreter", END)
text_to_sql_workflow.add_edge("error_handler", END)

# Compile the graph
text_to_sql_graph = text_to_sql_workflow.compile()