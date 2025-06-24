"""
Schema analyzer node for Text-to-SQL agent.
Analyzes database schema and determines relevant tables for queries.
"""
from typing import Dict, Any
import logging

from ...tools.schema_inspector import schema_inspector
from ...config import config
from ..state import TextToSQLState

logger = logging.getLogger(__name__)


def schema_analyzer_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Analyze database schema and determine relevant tables for the query.
    
    This node:
    1. Extracts relevant tables based on the natural language query
    2. Gets detailed schema information for those tables
    3. Formats schema context for the LLM
    4. Analyzes table relationships
    """
    try:
        query = state.get("original_query", "")
        if not query:
            logger.error("No original query provided to schema analyzer")
            return {
                "relevant_tables": [],
                "schema_context": "No query provided for schema analysis",
                "table_relationships": {},
                "reasoning_log": []
            }
        
        logger.info(f"Analyzing schema for query: {query[:100]}...")
        
        # 1. Determine relevant tables
        relevant_tables = schema_inspector.get_relevant_tables(
            query, 
            max_tables=config.agent.max_relevant_tables
        )
        
        if not relevant_tables:
            logger.warning("No relevant tables found for query")
            # Get a few sample tables as fallback
            all_tables = schema_inspector.get_all_tables_info(include_sample_data=False)
            relevant_tables = list(all_tables.keys())[:3]
        
        logger.info(f"Selected relevant tables: {relevant_tables}")
        
        # 2. Get detailed schema context
        schema_context = schema_inspector.format_schema_for_llm(
            table_names=relevant_tables,
            include_sample_data=config.agent.include_sample_data
        )
        
        # 3. Analyze table relationships
        all_relationships = schema_inspector.get_table_relationships()
        table_relationships = {
            table: all_relationships.get(table, {})
            for table in relevant_tables
        }
        
        # 4. Add metadata about the analysis
        analysis_metadata = {
            "total_tables_analyzed": len(relevant_tables),
            "schema_context_length": len(schema_context),
            "has_relationships": any(
                rel.get('references') or rel.get('referenced_by')
                for rel in table_relationships.values()
            )
        }
        
        logger.info(f"Schema analysis complete: {analysis_metadata}")
        
        # Log the reasoning step
        reasoning_step = {
            "step_name": "Schema Analysis",
            "details": f"Identified {len(relevant_tables)} relevant tables: {', '.join(relevant_tables)}.",
            "status": "✅"
        }
        
        return {
            "relevant_tables": relevant_tables,
            "schema_context": schema_context,
            "table_relationships": table_relationships,
            "schema_analysis_metadata": analysis_metadata,
            "reasoning_log": [reasoning_step]
        }
        
    except Exception as e:
        logger.error(f"Schema analysis failed: {str(e)}")
        return {
            "relevant_tables": [],
            "schema_context": f"Schema analysis failed: {str(e)}",
            "table_relationships": {},
            "validation_errors": [f"Schema analysis error: {str(e)}"],
            "reasoning_log": []
        }