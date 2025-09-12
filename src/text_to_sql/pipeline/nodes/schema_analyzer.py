"""
Schema analyzer node for Text-to-SQL pipeline.
"""
from typing import Dict, Any
import logging
import os
import time

from ...tools.semantic_table_finder import SemanticTableFinder
from ...tools.database_toolkit import db_toolkit
from ...config import config
from ..state import TextToSQLState
from ...database.engine import get_engine

logger = logging.getLogger(__name__)


class SchemaAnalyzer:
    """Schema analyzer using embeddings for semantic table selection."""
    
    def __init__(self):
        """Initialize the analyzer with embedding support (required)."""
        engine = get_engine()
        self.semantic_finder = SemanticTableFinder(
            engine=engine,
            model_name=os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2"),
            cache_dir=os.getenv("EMBEDDING_CACHE_DIR", ".embeddings_cache")
        )
        logger.info("Initialized embedding-based schema analyzer")
    
    def analyze_schema(self, query: str) -> Dict[str, Any]:
        """
        Analyze schema using embeddings for semantic table selection.
        
        Args:
            query: Natural language query
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing schema for: {query[:100]}...")
        
        # Find relevant tables using embeddings
        relevant_results = self._find_relevant_tables(query)
        
        # If no relevant tables found, treat as analysis error
        if not relevant_results:
            logger.info(f"No relevant tables found for query: {query[:50]}...")
            
            # Get available tables for error message
            all_tables = list(self.semantic_finder.table_embeddings.keys())
            table_list = ", ".join(all_tables[:8])
            if len(all_tables) > 8:
                table_list += f" (and {len(all_tables) - 8} more)"
            
            error_message = f"No relevant tables found for this query. Available tables: {table_list}"
            
            return {
                "schema_analysis_error": error_message,
                "reasoning_log": []
            }
        
        # Extract tables and scores directly
        relevant_tables = []
        relevance_scores = {}
        for table_name, score, _ in relevant_results:
            relevant_tables.append(table_name)
            relevance_scores[table_name] = score
        
        logger.info(f"Selected {len(relevant_tables)} tables: {', '.join(relevant_tables[:3])}...")
        
        # Build schema context with relationship expansion
        schema_context = self._build_schema_context(relevant_tables, relevance_scores)
        
        return {
            "schema_context": schema_context,
            "relevance_scores": relevance_scores,
        }
    
    def _find_relevant_tables(self, query: str):
        """Find tables relevant to the query using embeddings."""
        return self.semantic_finder.find_relevant_tables(
            query=query,
            max_tables=config.pipeline.max_relevant_tables,
            threshold=config.pipeline.relevance_threshold
        )
    def _expand_tables_via_relationships(self, relevant_tables: list) -> set:
        """Expand to include FK-connected tables."""
        all_relationships = db_toolkit.get_table_relationships()
        expanded_tables = set(relevant_tables)
        
        # Add tables connected via foreign keys
        for table in relevant_tables:
            relationships = all_relationships.get(table, {})
            
            # Add FK targets and sources
            for rel_type in ['references', 'referenced_by']:
                if rel_type in relationships:
                    for ref in relationships[rel_type]:
                        if 'table' in ref:
                            expanded_tables.add(ref['table'])
        
        if len(expanded_tables) > len(relevant_tables):
            new_tables = expanded_tables - set(relevant_tables)
            logger.info(f"Expanded tables via FK relationships: added {new_tables}")
        
        return expanded_tables
    
    def _build_schema_context(self, relevant_tables: list, relevance_scores: dict) -> str:
        """Build complete schema context for LLM with relationship expansion."""
        # First expand tables to include FK-connected tables
        expanded_tables = self._expand_tables_via_relationships(relevant_tables)
        
        # Format schema for LLM consumption
        schema_context = self._format_schema_for_llm(
            table_names=list(expanded_tables),
            include_sample_data=config.pipeline.include_sample_data
        )
        
        # Add relevance scores to context
        if relevance_scores:
            score_context = "\n\nTable Relevance Scores:\n"
            for table in relevant_tables[:5]:
                score = relevance_scores.get(table, 0)
                score_context += f"- {table}: {score:.1%} relevant\n"
            schema_context = score_context + "\n" + schema_context
        
        return schema_context
    
    def _format_schema_for_llm(self, table_names: list, include_sample_data: bool = True) -> str:
        """
        Format database schema for LLM consumption.
        Helper function for schema formatting.
        """
        schema_parts = ["Database Schema:"]
        
        for table_name in table_names:
            table_info = db_toolkit.get_table_info(table_name)
            schema_parts.append(f"\n## Table: {table_name}")
            schema_parts.append(f"Rows: {table_info.get('row_count', 'Unknown')}")
            
            # Format columns
            columns = table_info.get('columns', [])
            if columns:
                schema_parts.append("Columns:")
                for col in columns:
                    col_line = f"  - {col['name']} ({col['type']}"
                    if col.get('nullable') == False:
                        col_line += ", NOT NULL"
                    if col.get('primary_key'):
                        col_line += ", PRIMARY KEY"
                    col_line += ")"
                    schema_parts.append(col_line)
            
            # Add sample data if requested
            if include_sample_data:
                sample_data = db_toolkit.get_sample_data(table_name, limit=3)
                if sample_data:
                    schema_parts.append("Sample data:")
                    for i, row in enumerate(sample_data, 1):
                        schema_parts.append(f"  {i}. {row}")
        
        return "\n".join(schema_parts)


# Global instance
analyzer_instance = None

def get_analyzer() -> SchemaAnalyzer:
    """Get or create the analyzer instance."""
    global analyzer_instance
    if analyzer_instance is None:
        analyzer_instance = SchemaAnalyzer()
    return analyzer_instance


def schema_analyzer_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Schema analyzer node that uses embeddings for semantic table selection.
    """
    def create_reasoning_step(tables: list, scores: dict) -> dict:
        """Create reasoning step for the analysis."""
        if tables:
            detail = (
                f"Used semantic embeddings to identify {len(tables)} relevant tables. "
                f"Top match: {tables[0]} ({scores.get(tables[0], 0):.1%} similarity)"
            )
        else:
            detail = "No relevant tables found for the query."
        
        return {
            "step_name": "Schema Analysis",
            "details": detail,
            "status": "✅" if tables else "⚠️"
        }
    
    query = state["original_query"]
    
    try:
        # Measure schema analysis time
        start_time = time.time()
        
        # Analyze schema using embeddings
        analyzer = get_analyzer()
        analysis_result = analyzer.analyze_schema(query=query)
        
        schema_analysis_time_ms = (time.time() - start_time) * 1000
        
        # Check if schema analysis found an error
        if "schema_analysis_error" in analysis_result:
            return {
                "schema_analysis_error": analysis_result["schema_analysis_error"],
                "schema_analysis_time_ms": schema_analysis_time_ms,
                "reasoning_log": analysis_result.get("reasoning_log", [])
            }
        
        # Extract results for successful analysis
        schema_context = analysis_result["schema_context"] 
        relevance_scores = analysis_result.get("relevance_scores", {})
        relevant_tables = list(relevance_scores.keys()) if relevance_scores else []
        
        # Create reasoning step
        reasoning_step = create_reasoning_step(relevant_tables, relevance_scores)
        
        return {
            "schema_context": schema_context,
            "relevance_scores": relevance_scores,
            "schema_analysis_time_ms": schema_analysis_time_ms,
            "reasoning_log": [reasoning_step]
        }
        
    except Exception as e:
        logger.error(f"Schema analysis failed: {str(e)}")
        
        # Return error state - graph will route to error handler
        return {
            "schema_analysis_error": str(e),
            "reasoning_log": []
        }
