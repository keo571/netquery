from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal


class QueryClassification(BaseModel):
    """Schema for query classification results."""
    primary_intent: str = Field(
        description="Primary intent classification: sql, rag, mixed, or general"
    )
    secondary_intents: List[str] = Field(
        description="Additional intent classifications if any"
    )
    confidence: float = Field(
        description="Confidence score for the classification (0.0 to 1.0)"
    )
    complexity: str = Field(
        description="Complexity level: simple, medium, or complex"
    )
    requires_multiple_agents: bool = Field(
        description="Whether this query requires multiple agents"
    )
    rationale: str = Field(
        description="Brief explanation of the classification decision"
    )


class RoutingDecision(BaseModel):
    """Schema for agent routing decisions."""
    primary_agent: str = Field(
        description="Primary agent to handle the query"
    )
    secondary_agents: List[str] = Field(
        description="Additional agents that may be needed"
    )
    execution_mode: str = Field(
        description="Execution mode: single, parallel, or sequential"
    )
    rationale: str = Field(
        description="Explanation of the routing decision"
    )
    estimated_time: Optional[str] = Field(
        description="Estimated completion time in seconds",
        default=None
    )


class AgentCapability(BaseModel):
    """Schema for agent capability information."""
    agent_id: str = Field(description="Unique identifier for the agent")
    capabilities: List[str] = Field(description="List of agent capabilities")
    status: str = Field(description="Current status: available, busy, offline")
    load: float = Field(description="Current load percentage (0.0 to 1.0)")
    average_response_time: float = Field(description="Average response time in seconds")
    success_rate: float = Field(description="Success rate (0.0 to 1.0)")


class MCPServerStatus(BaseModel):
    """Schema for MCP server status information."""
    server_id: str = Field(description="MCP server identifier")
    status: str = Field(description="Server status: connected, disconnected, error")
    capabilities: List[str] = Field(description="Available capabilities")
    last_health_check: str = Field(description="Timestamp of last health check")
    error_count: int = Field(description="Number of recent errors", default=0)
    session_id: Optional[str] = Field(description="Active session ID if connected", default=None)


class RouteQuery(BaseModel):
    """Route a user query to the appropriate agent."""

    category: Literal["sql", "rag", "general"] = Field(
        ...,
        description=(
            "Given a user query, classify it as either 'sql' for database queries, "
            "'rag' for knowledge base questions, or 'general' for conversational topics."
        ),
    )