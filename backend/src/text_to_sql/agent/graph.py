"""
Text-to-SQL agent graph implementation.
Uses existing node implementations from the nodes directory.
"""
from langgraph.graph import StateGraph, START, END
from typing import Literal

from .state import TextToSQLState
from .nodes.schema_analyzer import schema_analyzer_node
from .nodes.query_planner import query_planner_node  
from .nodes.sql_generator import sql_generator_node
from .nodes.validator import validator_node
from .nodes.executor import executor_node
from .nodes.interpreter import interpret_results_node

def route_after_validation(state: TextToSQLState) -> Literal["executor", "interpreter"]:
    """Route based on validation results."""
    validation_errors = state.get("validation_errors", [])
    
    # If there are critical validation errors, skip execution
    if any("CRITICAL" in error for error in validation_errors):
        return "interpreter"
    
    return "executor"

# Create the workflow
text_to_sql_workflow = StateGraph(TextToSQLState)

# Add all nodes
text_to_sql_workflow.add_node("schema_analyzer", schema_analyzer_node)
text_to_sql_workflow.add_node("query_planner", query_planner_node)
text_to_sql_workflow.add_node("sql_generator", sql_generator_node)
text_to_sql_workflow.add_node("validator", validator_node)
text_to_sql_workflow.add_node("executor", executor_node)
text_to_sql_workflow.add_node("interpret_results", interpret_results_node)

# Add edges
text_to_sql_workflow.add_edge(START, "schema_analyzer")
text_to_sql_workflow.add_edge("schema_analyzer", "query_planner")
text_to_sql_workflow.add_edge("query_planner", "sql_generator")
text_to_sql_workflow.add_edge("sql_generator", "validator")

# Conditional routing after validation
text_to_sql_workflow.add_conditional_edges(
    "validator",
    route_after_validation,
    {
        "executor": "executor",
        "interpreter": "interpret_results"
    }
)

text_to_sql_workflow.add_edge("executor", "interpret_results")
text_to_sql_workflow.add_edge("interpret_results", END)

# Compile the graph
text_to_sql_graph = text_to_sql_workflow.compile()