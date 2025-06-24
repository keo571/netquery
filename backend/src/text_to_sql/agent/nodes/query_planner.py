"""
Query planner node for Text-to-SQL agent.
Analyzes the natural language query and creates a detailed query plan.
"""
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import logging
import re

from ...config import config
from ..state import TextToSQLState, QueryPlan

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
    try:
        query = state.get("natural_language_query", "")
        relevant_tables = state.get("relevant_tables", [])
        schema_context = state.get("schema_context", "")
        
        if not query:
            return {"validation_errors": ["No query provided for planning"]}
        
        logger.info(f"Planning query: {query[:100]}...")
        
        # Initialize LLM for query planning
        llm = ChatGoogleGenerativeAI(
            model=config.llm.model_name,
            temperature=0.1,
            max_tokens=800,
            api_key=config.llm.effective_api_key
        )
        
        # Create planning prompt
        planning_prompt = _create_planning_prompt(query, schema_context, relevant_tables)
        
        # Get query plan from LLM
        response = llm.invoke(planning_prompt)
        plan_text = response.content.strip()
        
        # Parse the response
        query_plan = _parse_query_plan(plan_text)
        
        # Analyze complexity
        complexity_assessment = _assess_complexity(query, query_plan, relevant_tables)
        
        # Determine if joins are required
        requires_joins = _requires_joins(query_plan, relevant_tables)
        
        # Estimate result size
        estimated_result_size = _estimate_result_size(query_plan, relevant_tables)
        
        logger.info(f"Query plan created: {complexity_assessment} complexity, "
                   f"joins={'yes' if requires_joins else 'no'}")
        
        # Log the reasoning step
        reasoning_step = {
            "step_name": "Query Planning",
            "details": f"Created a plan with intent '{query_plan.get('intent')}' and complexity '{query_plan.get('complexity')}'.",
            "status": "✅"
        }

        return {
            "query_plan": query_plan,
            "complexity_assessment": complexity_assessment,
            "requires_joins": requires_joins,
            "estimated_result_size": estimated_result_size,
            "reasoning_log": [reasoning_step]
        }
        
    except Exception as e:
        logger.error(f"Query planning failed: {str(e)}")
        return {
            "query_plan": {},
            "complexity_assessment": "unknown",
            "requires_joins": False,
            "estimated_result_size": None,
            "validation_errors": [f"Query planning error: {str(e)}"]
        }


def _create_planning_prompt(query: str, schema_context: str, tables: List[str]) -> str:
    """Create the query planning prompt for the LLM."""
    return f"""You are a SQL query planner. Analyze the natural language query and create a detailed execution plan.

Natural Language Query: {query}

Available Schema:
{schema_context}

Instructions:
1. Identify the main intent (select, aggregate, filter, join, etc.)
2. Determine which tables and columns are needed
3. Identify any filters, aggregations, or sorting requirements
4. Determine if joins are needed and what type
5. Assess the complexity level

Respond with a JSON object containing:
- intent: main query intent
- target_tables: list of tables needed
- required_columns: list of columns needed
- filters: list of filter conditions
- aggregations: list of aggregation operations
- sorting: sorting requirements
- grouping: grouping requirements
- joins: list of join operations needed
- estimated_complexity: "simple", "medium", or "complex"

Example:
{{
    "intent": "select_with_filter",
    "target_tables": ["employees"],
    "required_columns": ["first_name", "last_name", "salary"],
    "filters": [
        {{"column": "department", "operator": "=", "value": "Engineering"}}
    ],
    "aggregations": [],
    "sorting": {{"column": "salary", "direction": "DESC"}},
    "grouping": null,
    "joins": [],
    "estimated_complexity": "simple"
}}

Query to plan: {query}
"""


def _parse_query_plan(plan_text: str) -> QueryPlan:
    """Parse the LLM response into a QueryPlan object."""
    try:
        # Extract JSON from the response
        json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            
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
        else:
            logger.warning("No JSON found in query plan response")
            return _create_fallback_plan()
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse query plan JSON: {str(e)}")
        return _create_fallback_plan()


def _create_fallback_plan() -> QueryPlan:
    """Create a fallback query plan when parsing fails."""
    return QueryPlan(
        intent="unknown",
        target_tables=[],
        required_columns=[],
        filters=[],
        aggregations=[],
        sorting=None,
        grouping=None,
        joins=[],
        estimated_complexity="medium"
    )


def _assess_complexity(query: str, query_plan: QueryPlan, tables: List[str]) -> str:
    """Assess query complexity based on various factors."""
    complexity_score = 0
    
    # Base complexity from plan
    plan_complexity = query_plan.get("estimated_complexity", "medium")
    if plan_complexity == "simple":
        complexity_score += 1
    elif plan_complexity == "medium":
        complexity_score += 2
    else:  # complex
        complexity_score += 3
    
    # Table count
    table_count = len(tables)
    if table_count > 3:
        complexity_score += 2
    elif table_count > 1:
        complexity_score += 1
    
    # Join count
    join_count = len(query_plan.get("joins", []))
    complexity_score += join_count
    
    # Aggregation count
    agg_count = len(query_plan.get("aggregations", []))
    complexity_score += agg_count
    
    # Filter complexity
    filter_count = len(query_plan.get("filters", []))
    if filter_count > 3:
        complexity_score += 1
    
    # Subquery detection in original query
    if re.search(r'\(\s*SELECT\b', query.upper()):
        complexity_score += 2
    
    # Determine final complexity
    if complexity_score <= 2:
        return "simple"
    elif complexity_score <= 5:
        return "medium"
    else:
        return "complex"


def _requires_joins(query_plan: QueryPlan, tables: List[str]) -> bool:
    """Determine if the query requires joins."""
    # Check if plan explicitly mentions joins
    if query_plan.get("joins"):
        return True
    
    # Check if multiple tables are involved
    target_tables = query_plan.get("target_tables", [])
    if len(target_tables) > 1:
        return True
    
    # Check if tables list has multiple tables
    if len(tables) > 1:
        return True
    
    return False


def _estimate_result_size(query_plan: QueryPlan, tables: List[str]) -> int:
    """Estimate the number of result rows."""
    # This is a simple estimation - in a real system you'd use table statistics
    base_size = 100  # Default estimate
    
    # Adjust based on filters
    filter_count = len(query_plan.get("filters", []))
    if filter_count > 0:
        # Each filter typically reduces result size
        base_size = base_size // (2 ** filter_count)
    
    # Adjust based on aggregations
    if query_plan.get("aggregations"):
        # Aggregations typically produce fewer rows
        base_size = min(base_size, 50)
    
    # Adjust based on grouping
    if query_plan.get("grouping"):
        # Grouping typically produces moderate number of rows
        base_size = min(base_size, 200)
    
    # Adjust based on joins
    join_count = len(query_plan.get("joins", []))
    if join_count > 0:
        # Joins can increase or decrease result size
        base_size = base_size * (join_count + 1)
    
    return max(1, min(base_size, 10000))  # Clamp between 1 and 10,000