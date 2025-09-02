"""
SQL generator node for Text-to-SQL pipeline.
Generates SQL queries from natural language using LLM.
"""
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
import re
import logging

from ...config import config
from ..state import TextToSQLState
from ...utils.sql_utils import extract_sql_from_response, format_sql_query, optimize_sql_query
from ...prompts.sql_generation import SQL_GENERATION_PROMPT

logger = logging.getLogger(__name__)


def sql_generator_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Generate SQL query from natural language using LLM with schema context.
    
    This node:
    1. Uses the query plan and schema context to generate SQL
    2. Applies best practices and optimization hints
    3. Includes explanation of the generated query
    4. Provides confidence score for the generation
    """
    try:
        query = state.get("original_query", "")
        schema_context = state.get("schema_context", "")
        query_plan = state.get("query_plan", {})
        relevant_tables = state.get("relevant_tables", [])
        
        if not query:
            return {"validation_errors": ["No query provided for SQL generation"]}
        
        if not schema_context:
            return {"validation_errors": ["No schema context available for SQL generation"]}
        
        logger.info(f"Generating SQL for query: {query[:100]}...")
        
        # Initialize LLM for SQL generation
        llm = ChatGoogleGenerativeAI(
            model=config.llm.model_name,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            max_retries=config.llm.max_retries,
            api_key=config.llm.effective_api_key
        )
        
        # Create SQL generation prompt
        sql_prompt = _create_sql_generation_prompt(
            query, schema_context, query_plan, relevant_tables
        )
        
        # Generate SQL
        response = llm.invoke(sql_prompt)
        response_text = response.content.strip()
        
        # Extract and clean SQL using utility function
        generated_sql = extract_sql_from_response(response_text)
        
        # Format SQL for readability
        generated_sql = format_sql_query(generated_sql)
        
        # Get optimization suggestions
        optimization_result = optimize_sql_query(generated_sql, {'max_result_rows': config.safety.max_result_rows})
        if optimization_result['has_optimizations']:
            generated_sql = optimization_result['optimized_query']
            logger.info(f"Applied optimizations: {', '.join(optimization_result['suggestions'])}")
        
        # Extract explanation
        sql_explanation = _extract_explanation(response_text)
        
        # Calculate confidence score
        confidence_score = _calculate_confidence_score(generated_sql, query_plan, schema_context)
        
        logger.info(f"SQL generated successfully with confidence {confidence_score:.2f}")
        
        # Log the reasoning step
        reasoning_step = {
            "step_name": "SQL Generation",
            "details": "Successfully generated the SQL query based on the plan and schema.",
            "status": "✅"
        }
        
        return {
            "generated_sql": generated_sql,
            "sql_explanation": sql_explanation,
            "confidence_score": confidence_score,
            "reasoning_log": [reasoning_step]
        }
        
    except Exception as e:
        logger.error(f"SQL generation failed: {str(e)}")
        return {
            "generated_sql": "",
            "sql_explanation": f"SQL generation failed: {str(e)}",
            "confidence_score": 0.0,
            "validation_errors": [f"SQL generation error: {str(e)}"],
            "reasoning_log": []
        }


def _create_sql_generation_prompt(query: str, schema_context: str, 
                                query_plan: Dict[str, Any], tables: list) -> str:
    """Create the SQL generation prompt for the LLM."""
    
    # Include query plan context if available
    plan_context = ""
    if query_plan and query_plan.get("intent"):
        plan_context = f"""
Query Plan Analysis:
- Intent: {query_plan.get('intent', 'unknown')}
- Target Tables: {', '.join(query_plan.get('target_tables', []))}
- Required Columns: {', '.join(query_plan.get('required_columns', []))}
- Complexity: {query_plan.get('estimated_complexity', 'medium')}
- Requires Joins: {'Yes' if len(tables) > 1 else 'No'}
"""
    
    # Use the prompt template
    return SQL_GENERATION_PROMPT.format(
        schema_context=schema_context,
        plan_context=plan_context,
        query=query,
        max_rows=config.safety.max_result_rows
    )




def _extract_explanation(response_text: str) -> str:
    """Extract explanation from LLM response."""
    # Look for explanation section
    explanation_match = re.search(r'Explanation:\s*(.*?)(?:\n\n|$)', response_text, re.DOTALL | re.IGNORECASE)
    if explanation_match:
        return explanation_match.group(1).strip()
    
    # Look for text after SQL block
    sql_block_match = re.search(r'```sql.*?```\s*(.*)', response_text, re.DOTALL | re.IGNORECASE)
    if sql_block_match:
        explanation = sql_block_match.group(1).strip()
        if explanation and len(explanation) > 10:
            return explanation
    
    # Fallback: generate basic explanation
    return "SQL query generated to retrieve the requested data from the database."


def _calculate_confidence_score(sql_query: str, query_plan: Dict[str, Any], schema_context: str) -> float:
    """Calculate confidence score for the generated SQL."""
    if not sql_query:
        return 0.0
    
    score = 1.0
    sql_upper = sql_query.upper()
    
    # Basic syntax checks
    if not sql_upper.startswith('SELECT'):
        score -= 0.3
    
    if 'FROM' not in sql_upper:
        score -= 0.4
    
    # Check for required elements based on query plan
    if query_plan:
        target_tables = query_plan.get('target_tables', [])
        for table in target_tables:
            if table.upper() not in sql_upper:
                score -= 0.2
        
        # Check for filters if plan indicates them
        if query_plan.get('filters') and 'WHERE' not in sql_upper:
            score -= 0.2
        
        # Check for joins if multiple tables
        if len(target_tables) > 1 and 'JOIN' not in sql_upper:
            score -= 0.3
        
        # Check for aggregations if plan indicates them
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']
        if query_plan.get('aggregations'):
            has_aggregation = any(func in sql_upper for func in agg_functions)
            if not has_aggregation:
                score -= 0.2
    
    # Bonus for good practices
    if 'LIMIT' in sql_upper:
        score += 0.1
    
    if 'JOIN' in sql_upper and len(re.findall(r'\bJOIN\b', sql_upper)) > 0:
        score += 0.05  # Explicit joins
    
    # Penalty for potential issues
    if 'SELECT *' in sql_upper:
        score -= 0.1
    
    if sql_query.count('(') != sql_query.count(')'):
        score -= 0.3  # Unbalanced parentheses
    
    return max(0.0, min(1.0, score))