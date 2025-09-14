"""
Query planner node for Text-to-SQL pipeline.
Analyzes the natural language query and creates a detailed query plan.
"""
from typing import Dict, Any
import json
import logging
import re
import time

from ..state import TextToSQLState, QueryPlan
from ...prompts import QUERY_PLANNING_PROMPT
from ...utils.llm_utils import get_llm_with_config

logger = logging.getLogger(__name__)


def query_planner_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Create a detailed query plan based on the natural language query and schema.
    
    This node:
    1. Analyzes query intent and complexity
    2. Determines required tables and columns
    3. Identifies necessary joins and filters
    4. Estimates query complexity and result size
    """
    # Get validated inputs from previous nodes
    query = state["original_query"]  # From initial state
    schema_context = state["schema_context"]  # From schema_analyzer
    
    
    logger.info(f"Planning query: {query[:100]}...")
    
    try:
        # Measure query planning time
        start_time = time.time()
        
        # Get LLM instance with query planning specific config
        llm = get_llm_with_config(
            temperature=0.1,
            max_tokens=1500  # Increased for complete JSON responses
        )
        
        # Create planning prompt using organized template
        planning_prompt = QUERY_PLANNING_PROMPT.format(query=query, schema_context=schema_context)
        
        # Get query plan from LLM
        response = llm.invoke(planning_prompt)
        plan_text = response.content.strip() if response.content else ""

        query_planning_time_ms = (time.time() - start_time) * 1000

        if not plan_text:
            raise ValueError("Empty response from LLM")
        
        # Parse the response
        query_plan = _parse_query_plan(plan_text)
        
        # Use LLM's complexity assessment
        complexity_assessment = query_plan.get("estimated_complexity", "medium")
        
        logger.info(f"Query plan created: {complexity_assessment} complexity")
        
        # Log the reasoning step
        reasoning_step = {
            "step_name": "Query Planning",
            "details": f"Created a plan with intent '{query_plan.get('intent')}' and complexity '{query_plan.get('estimated_complexity')}'.",
            "status": "✅"
        }

        return {
            "query_plan": query_plan,
            "complexity_assessment": complexity_assessment,
            "query_planning_time_ms": query_planning_time_ms,
            "reasoning_log": [reasoning_step]
        }
        
    except Exception as e:
        logger.error(f"Query planning failed: {str(e)}")
        
        # Return error state - graph will route to error_handler
        return {
            "planning_error": str(e),
            "reasoning_log": []
        }


def _parse_query_plan(plan_text: str) -> QueryPlan:
    """Parse the LLM response into a QueryPlan object."""
    # Clean the response and look for JSON
    clean_text = plan_text.strip()
    
    # Remove markdown code blocks if present
    clean_text = re.sub(r'```json\s*', '', clean_text)
    clean_text = re.sub(r'```\s*$', '', clean_text)
    clean_text = clean_text.strip()
    
    # If the whole response looks like JSON, use it directly
    if clean_text.startswith('{') and clean_text.endswith('}'):
        json_str = clean_text
    else:
        # Try to find JSON within the text
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Basic nested JSON
            r'\{.*\}',  # Simple JSON (fallback)
        ]
        
        json_str = None
        for pattern in json_patterns:
            json_match = re.search(pattern, clean_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                break
    
    if not json_str:
        raise ValueError("No JSON found in query plan response")
    
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in query plan response: {e}")
    
    return QueryPlan(
        intent=parsed.get("intent", "unknown"),
        target_tables=parsed.get("target_tables", []),
        required_columns=parsed.get("required_columns", []),
        filters=parsed.get("filters", []),
        aggregations=parsed.get("aggregations", []),
        sorting=parsed.get("sorting"),
        grouping=parsed.get("grouping"),
        joins=parsed.get("joins", []),
        estimated_complexity=parsed.get("estimated_complexity", "medium")
    )




