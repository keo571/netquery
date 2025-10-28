"""
Pydantic schemas for structured LLM output in interpretation service.
Using structured output ensures JSON validity and type safety.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class GroupingConfig(BaseModel):
    """Configuration for data grouping in visualizations."""
    enabled: bool = Field(description="Whether to enable grouping on categorical data")
    group_by_column: Optional[str] = Field(default=None, description="Column to group by if enabled")
    original_column: Optional[str] = Field(default=None, description="Original column name if grouping")


class VisualizationConfig(BaseModel):
    """Configuration for chart visualization."""
    x_column: str = Field(description="Column to use for x-axis")
    y_column: Optional[str] = Field(default=None, description="Column to use for y-axis")
    reason: str = Field(description="Explanation of why this visualization works best")
    grouping: Optional[GroupingConfig] = Field(default=None, description="Grouping configuration for categorical data")


class Visualization(BaseModel):
    """Visualization recommendation for query results."""
    type: Literal["bar", "line", "pie", "scatter", "none"] = Field(
        description="Type of chart to display"
    )
    title: str = Field(description="Title for the chart")
    config: Optional[VisualizationConfig] = Field(
        default=None,
        description="Configuration for the chart (required unless type is 'none')"
    )


class InterpretationResponse(BaseModel):
    """Complete interpretation response with analysis and visualization."""
    summary: str = Field(
        description="Direct 1-sentence answer to the query"
    )
    key_findings: List[str] = Field(
        description="List of 2-4 critical insights with specific values",
        max_length=4
    )
    visualization: Visualization = Field(
        description="Visualization recommendation for the data"
    )
