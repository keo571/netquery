"""
Routing node for Manager agent.
Directs the conversation to the appropriate agent based on classification.
"""
from typing import Dict, Any

from ..state import ManagerState


def route_to_agents_node(state: ManagerState) -> Dict[str, Any]:
    """
    Routes the query to the correct agent based on classification.
    """
    # Get the classification from the classifier node
    classification = state["query_classification"]
    
    # Map classification to specific agent
    if classification == "sql":
        agent_to_execute = "text_to_sql"
    elif classification == "rag":
        agent_to_execute = "rag"
    else:
        # This shouldn't happen given the graph routing, but just in case
        agent_to_execute = "general"
    
    # Return the agent_to_execute that the executor node expects
    return {"agent_to_execute": agent_to_execute} 