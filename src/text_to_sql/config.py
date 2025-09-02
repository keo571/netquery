"""
Configuration for the Text-to-SQL pipeline.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration."""
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{Path(__file__).parent / 'infrastructure.db'}",
        description="Database connection URL"
    )
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")


class LLMConfig(BaseModel):
    """LLM configuration."""
    model_name: str = Field(default="gemini-1.5-flash", description="Model name")
    temperature: float = Field(default=0.1, description="Temperature for generation")
    max_tokens: int = Field(default=2048, description="Maximum tokens")
    max_retries: int = Field(default=3, description="Maximum retries")
    
    @property
    def effective_api_key(self) -> str:
        """Get the effective API key."""
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return api_key


class PipelineConfig(BaseModel):
    """Pipeline-specific configuration."""
    max_relevant_tables: int = Field(default=5, description="Maximum tables to analyze")
    relevance_threshold: float = Field(default=0.1, description="Relevance threshold")
    include_sample_data: bool = Field(default=True, description="Include sample data")
    
    # Additional fields for existing code
    cache_schema: bool = Field(default=True, description="Enable schema caching")
    schema_cache_ttl: int = Field(default=3600, description="Schema cache TTL in seconds")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")  # Add this line
    max_query_plan_steps: int = Field(default=10, description="Maximum query plan steps")
    enable_query_optimization: bool = Field(default=True, description="Enable query optimization")
    complexity_analysis: bool = Field(default=True, description="Enable complexity analysis")
    max_execution_time: int = Field(default=30, description="Maximum execution time in seconds")


class SafetyConfig(BaseModel):
    """Safety configuration."""
    max_result_rows: int = Field(default=50, description="Maximum result rows")
    allowed_operations: list = Field(default=["SELECT"], description="Allowed SQL operations")
    
    # Additional fields for the existing safety validator
    blocked_keywords: list = Field(
        default=[
            "DELETE", "DROP", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE",
            "REPLACE", "MERGE", "CALL", "EXEC", "EXECUTE", "DECLARE", "GRANT",
            "REVOKE", "COMMIT", "ROLLBACK", "SAVEPOINT", "SET", "SHOW", "USE",
            "DESCRIBE", "EXPLAIN", "LOCK", "UNLOCK", "KILL", "SHUTDOWN"
        ],
        description="Blocked SQL keywords"
    )
    
    blocked_tables: list = Field(
        default=["sqlite_master", "sqlite_sequence", "information_schema"],
        description="Blocked table names"
    )
    
    blocked_columns: list = Field(
        default=["password", "passwd", "secret", "token", "key", "credential"],
        description="Blocked column patterns"
    )
    
    max_query_length: int = Field(default=10000, description="Maximum query length")
    max_joins: int = Field(default=5, description="Maximum number of joins")
    max_subqueries: int = Field(default=3, description="Maximum number of subqueries")
    max_union_operations: int = Field(default=2, description="Maximum UNION operations")


class TextToSQLConfig(BaseModel):
    """Main configuration."""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    
    # Legacy support
    @property
    def synthesis_model(self) -> str:
        return self.llm.model_name
    
    @property
    def gemini_api_key(self) -> str:
        return self.llm.effective_api_key
    
    # ADD: For compatibility with interpreter.py that expects GEMINI_MODEL
    @property
    def GEMINI_MODEL(self) -> str:
        return self.llm.model_name


# Global configuration instance
config = TextToSQLConfig()