from __future__ import annotations
from dataclasses import dataclass, field
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import add_messages
from typing_extensions import Annotated
import operator
from langchain_core.messages import BaseMessage


class ManagerState(TypedDict):
    """Main state for the manager agent that coordinates other agents."""
    messages: Annotated[List[BaseMessage], operator.add]
    original_query: str
    query_classification: str  # "sql", "rag", "mixed", "general"
    confidence_score: float
    run_config: Dict[str, Any]
    
    # Agent coordination
    active_agents: Annotated[List[str], operator.add]
    agent_responses: Annotated[List[Dict], operator.add]
    agent_sessions: Dict[str, str]  # agent_id -> session_id
    agent_to_execute: str
    
    # MCP coordination
    available_agents: Dict[str, Dict[str, Any]]  # agent capabilities
    routing_decision: Dict[str, Any]
    
    # Response synthesis
    synthesis_strategy: str  # "single", "parallel", "sequential"
    final_answer: str
    response_metadata: Dict[str, Any]
    include_reasoning: bool


class AgentResponse(TypedDict):
    """Response from a specialized agent."""
    agent_id: str
    session_id: str
    success: bool
    answer: str
    confidence: float
    reasoning_steps: List[Dict]
    sources: List[Dict]
    execution_time: float
    error_message: Optional[str]


class RoutingDecision(TypedDict):
    """Decision about which agents to use and how."""
    primary_agent: str
    secondary_agents: List[str]
    execution_mode: str  # "single", "parallel", "sequential"
    rationale: str


class QueryClassification(TypedDict):
    """Classification result for incoming query."""
    primary_intent: str
    secondary_intents: List[str]
    confidence: float
    complexity: str  # "simple", "medium", "complex"
    requires_multiple_agents: bool


@dataclass(kw_only=True)
class MCPServerInfo:
    """Information about connected MCP servers."""
    server_id: str
    status: str  # "connected", "disconnected", "error"
    capabilities: List[str]
    last_health_check: str
    session_id: Optional[str] = None
    error_count: int = 0