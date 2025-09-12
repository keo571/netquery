"""
Configuration for the Text-to-SQL pipeline.
"""
import os
from pathlib import Path
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration."""
    database_url: str = Field(
        default="sqlite:///infrastructure.db",
        description="Database connection URL (relative to project root)"
    )
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Convert relative SQLite paths to absolute for reliability
        if self.database_url.startswith('sqlite:///') and not self.database_url.startswith('sqlite:////'):
            rel_path = self.database_url[10:]  # Remove 'sqlite:///'
            
            # Get project root (where this config file's parent/parent directory is)
            project_root = Path(__file__).parent.parent.parent
            abs_path = project_root / rel_path
            self.database_url = f"sqlite:///{abs_path.resolve()}"


class LLMConfig(BaseModel):
    """LLM configuration."""
    model_name: str = Field(default="gemini-2.5-flash", description="Model name")
    temperature: float = Field(default=0.1, description="Temperature for generation")
    max_tokens: int = Field(default=4096, description="Maximum tokens")
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
    max_relevant_tables: int = Field(default=5, description="Maximum tables to return after filtering")
    relevance_threshold: float = Field(default=0.15, description="Minimum similarity threshold for table relevance (0-1). Uses two-stage filtering: gets 2x candidates, then filters by this threshold.")
    include_sample_data: bool = Field(default=True, description="Include sample data")
    max_execution_time: int = Field(default=30, description="Maximum execution time in seconds")


class SafetyConfig(BaseModel):
    """Safety configuration."""
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
    
# Global configuration instance
config = TextToSQLConfig()