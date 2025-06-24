"""
Manager agent graph implementation.
Simplified main graph using organized node structure.
"""
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from .state import ManagerState
from .nodes import (
    classify_query_node,
    route_to_agents_node,
    execute_single_agent_node,
    handle_general_query_node
)

load_dotenv()

if os.getenv("GEMINI_API_KEY") is None:
    raise ValueError("GEMINI_API_KEY is not set")


def route_after_classification(state: ManagerState) -> str:
    """Route based on query classification."""
    classification = state["query_classification"]
    
    if classification == "general":
        return "handle_general_query"
    else:
        return "route_to_agents"


# Create the manager workflow
manager_workflow = StateGraph(ManagerState)

# Add all nodes
manager_workflow.add_node("classify_query", classify_query_node)
manager_workflow.add_node("route_to_agents", route_to_agents_node)
manager_workflow.add_node("execute_single_agent", execute_single_agent_node)
manager_workflow.add_node("handle_general_query", handle_general_query_node)

# Add edges
manager_workflow.add_edge(START, "classify_query")

# Conditional routing after classification
manager_workflow.add_conditional_edges(
    "classify_query",
    route_after_classification,
    {
        "handle_general_query": "handle_general_query",
        "route_to_agents": "route_to_agents"
    }
)

# After routing, execute the chosen agent
manager_workflow.add_edge("route_to_agents", "execute_single_agent")

# The specialized agent's output is the final answer
manager_workflow.add_edge("execute_single_agent", END)

# Compile the graph
graph = manager_workflow.compile()