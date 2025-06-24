import os
from pydantic import BaseModel, Field
from typing import Any, Optional, Dict, List

from langchain_core.runnables import RunnableConfig


class ManagerConfiguration(BaseModel):
    """Configuration for the manager agent."""

    # LLM Configuration
    classification_model: str = Field(
        default="gemini-1.5-flash", # Free tier
        metadata={
            "description": "Model for query classification and intent recognition."
        },
    )

    routing_model: str = Field(
        default="gemini-1.5-flash", # Free tier
        metadata={
            "description": "Model for agent routing decisions."
        },
    )

    synthesis_model: str = Field(
        default="gemini-1.5-flash",  # Free tier, changed from gemini-2.5-pro-preview-05-06
        metadata={
            "description": "Model for synthesizing multi-agent responses."
        },
    )

    # Agent Management
    max_parallel_agents: int = Field(
        default=3,
        metadata={"description": "Maximum number of agents to run in parallel."},
    )

    agent_timeout: int = Field(
        default=120,
        metadata={"description": "Timeout for agent responses in seconds."},
    )

    health_check_interval: int = Field(
        default=30,
        metadata={"description": "Health check interval for MCP servers in seconds."},
    )

    # MCP Configuration
    mcp_server_configs: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "text_to_sql": {
                "command": ["python", "-m", "text_to_sql.mcp_server"],
                "capabilities": ["sql_execution", "schema_analysis", "query_planning"],
                "enabled": True,
                "auto_restart": True
            },
            "rag": {
                "command": ["python", "-m", "rag.mcp_server"],
                "capabilities": ["document_search", "embedding_generation", "citation_tracking"],
                "enabled": True,
                "auto_restart": True
            }
        },
        metadata={"description": "Configuration for MCP servers."}
    )

    # Classification Configuration
    classification_confidence_threshold: float = Field(
        default=0.7,
        metadata={"description": "Minimum confidence for query classification."}
    )

    multi_agent_threshold: float = Field(
        default=0.6,
        metadata={"description": "Threshold for triggering multi-agent responses."}
    )

    # Response Configuration
    max_response_tokens: int = Field(
        default=4000,
        metadata={"description": "Maximum tokens in synthesized response."}
    )

    include_reasoning_steps: bool = Field(
        default=True,
        metadata={"description": "Include agent reasoning steps in response."}
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "ManagerConfiguration":
        """Create a ManagerConfiguration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)