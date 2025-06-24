"""
Query planning node for Text-to-SQL agent.
Analyzes the user's query to determine its complexity and topic.
"""
from typing import Dict, Any

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

from ...config import config as text_to_sql_config
from ..state import ReasoningStep
from ..prompts import QUERY_PLANNING_PROMPT


class QueryPlan(BaseModel):
    """
    A plan for how to approach a natural language query.
    """
    main_topic: str = Field(
        description="The primary subject of the query (e.g., 'Load Balancers', 'Firewall Rules')."
    )
    complexity: str | None = Field(
        description="Estimated complexity of the query: 'simple', 'moderate', or 'complex'.",
        default=None
    )


def plan_query_node(state: dict, config: RunnableConfig) -> Dict[str, Any]:
    """
    Analyzes the user's query and creates a plan.
    """
    llm = ChatGoogleGenerativeAI(
        model=text_to_sql_config.GEMINI_MODEL,
        temperature=0.0,
        max_retries=2
    ).with_structured_output(QueryPlan)

    prompt = QUERY_PLANNING_PROMPT.format(query=state["original_query"])
    plan: QueryPlan = llm.invoke(prompt, config=config)

    # Build the summary string conditionally
    summary_parts = []
    if plan.complexity:
        summary_parts.append(f"Complexity: {plan.complexity}")

    if plan.main_topic:
        summary_parts.append(f"Topic: {plan.main_topic}")

    summary = ", ".join(summary_parts)
    if not summary:
        summary = "Initial analysis complete."

    # Log the reasoning step
    log_entry: ReasoningStep = {
        "step_name": "Query Planning",
        "summary": summary,
        "outcome": "success",
    }

    return {"reasoning_log": [log_entry]} 