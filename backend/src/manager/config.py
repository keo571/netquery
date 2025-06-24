"""
Configuration for the Manager agent.
Renamed from configuration.py for consistency with text_to_sql structure.
"""
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig


class LLMConfig(BaseModel):
    """LLM configuration for manager agent."""
    classification_model: str = Field(default="gemini-1.5-flash", description="Model for query classification")
    routing_model: str = Field(default="gemini-1.5-flash", description="Model for agent routing")  
    synthesis_model: str = Field(default="gemini-1.5-flash", description="Model for response synthesis")
    temperature: float = Field(default=0.1, description="Temperature for generation")
    max_retries: int = Field(default=2, description="Maximum retries for LLM calls")
    
    @property
    def effective_api_key(self) -> str:
        """Get the effective API key."""
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return api_key


class RoutingConfig(BaseModel):
    """Configuration for agent routing."""
    enable_multi_agent: bool = Field(default=True, description="Enable multi-agent execution")
    max_concurrent_agents: int = Field(default=3, description="Maximum concurrent agents")
    agent_timeout: int = Field(default=30, description="Agent timeout in seconds")
    fallback_to_general: bool = Field(default=True, description="Fallback to general handler on errors")


class ManagerConfig(BaseModel):
    """Main manager agent configuration."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    
    # Legacy compatibility
    @property
    def classification_model(self) -> str:
        return self.llm.classification_model
    
    @property
    def routing_model(self) -> str:
        return self.llm.routing_model
        
    @property
    def synthesis_model(self) -> str:
        return self.llm.synthesis_model
    
    # ADD: For compatibility with classifier.py that expects GEMINI_MODEL
    @property
    def GEMINI_MODEL(self) -> str:
        return self.llm.classification_model


# For backward compatibility, keep the old class name as an alias
class ManagerConfiguration(ManagerConfig):
    """Legacy alias for ManagerConfig."""
    
    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig]) -> "ManagerConfiguration":
        """Create configuration from runnable config."""
        if config and hasattr(config, 'configurable'):
            configurable = config.configurable or {}
            return cls(**configurable)
        return cls()


# Global configuration instance
config = ManagerConfig() 