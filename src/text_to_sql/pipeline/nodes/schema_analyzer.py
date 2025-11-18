"""
Schema analyzer node for Text-to-SQL pipeline.
"""
from typing import Dict, Any, Optional
import logging
import os
import time
from pathlib import Path

from ...tools.semantic_table_finder import SemanticTableFinder
from ...tools.database_toolkit import GenericDatabaseToolkit, get_db_toolkit
from src.schema_ingestion.canonical import CanonicalSchema
from ....common.config import config
from ....common.schema_summary import get_schema_overview, _resolve_schema_path
from ..state import TextToSQLState, create_success_step, create_warning_step

logger = logging.getLogger(__name__)


class SchemaAnalyzer:
    """Schema analyzer using embeddings for semantic table selection."""

    def __init__(self, canonical_schema_path: Optional[str] = None,
                 db_toolkit: Optional[GenericDatabaseToolkit] = None,
                 query_cache: Optional[Any] = None):
        """
        Initialize the analyzer with embedding support (required).

        Args:
            canonical_schema_path: Path to canonical schema file
            db_toolkit: Database toolkit instance (uses default if None)
            query_cache: Optional query cache instance (shared across pipeline)
        """
        self.canonical_schema: Optional[CanonicalSchema] = None
        if canonical_schema_path:
            self._load_canonical_schema(canonical_schema_path)

        # Create SemanticTableFinder with canonical schema for embedding
        if self.canonical_schema is None:
            raise ValueError(
                "SchemaAnalyzer requires a canonical schema with table and column descriptions. "
                "Provide canonical_schema_path or set CANONICAL_SCHEMA_PATH."
            )

        # Pass query cache to semantic finder (if provided)
        self.semantic_finder = SemanticTableFinder(
            model_name=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
            cache_dir=os.getenv("EMBEDDING_CACHE_DIR", ".embeddings_cache"),
            canonical_schema=self.canonical_schema,
            query_cache=query_cache
        )

        # Dependency injection: use provided toolkit or get default
        self.db_toolkit = db_toolkit or get_db_toolkit()

        # Provide canonical schema to db_toolkit for FK fallback
        # (Critical for production DBs without FK constraints)
        self.db_toolkit.set_canonical_schema(self.canonical_schema)

        logger.info(
            "Initialized embedding-based schema analyzer (canonical_schema: %s, db_toolkit: %s)",
            self.canonical_schema is not None,
            type(self.db_toolkit).__name__
        )

    def _load_canonical_schema(self, canonical_schema_path: str):
        """Load canonical schema for enhanced descriptions and namespace isolation."""
        try:
            if not Path(canonical_schema_path).exists():
                logger.warning(f"Canonical schema file not found: {canonical_schema_path}")
                return

            self.canonical_schema = CanonicalSchema.load(canonical_schema_path)
            logger.info(
                "Loaded canonical schema '%s' with %s tables",
                self.canonical_schema.schema_id,
                self.canonical_schema.total_tables
            )
        except Exception as exc:
            logger.error(f"Failed to load canonical schema: {exc}")
            self.canonical_schema = None
    
    def analyze_schema(self, query: str, cached_embedding: Optional[list] = None) -> Dict[str, Any]:
        """
        Analyze schema using embeddings for semantic table selection.

        Args:
            query: Natural language query
            cached_embedding: Pre-computed embedding (if available from cache)

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing schema for: {query[:100]}...")

        # Find relevant tables using embeddings (use cached if available)
        relevant_results = self._find_relevant_tables(query, cached_embedding)
        
        # If no relevant tables found, treat as analysis error
        if not relevant_results:
            logger.info(f"No relevant tables found for query: {query[:30]}...")
            
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
        for table_name, score in relevant_results:
            relevant_tables.append(table_name)
            relevance_scores[table_name] = score
        
        logger.info(f"Selected {len(relevant_tables)} tables: {', '.join(relevant_tables[:3])}...")
        
        # Build schema context with relationship expansion
        schema_context = self._build_schema_context(relevant_tables, relevance_scores)
        
        return {
            "schema_context": schema_context,
            "relevance_scores": relevance_scores,
        }
    
    def _find_relevant_tables(self, query: str, cached_embedding: Optional[list] = None):
        """Find tables relevant to the query using embeddings."""
        return self.semantic_finder.find_relevant_tables(
            query=query,
            max_tables=config.pipeline.max_relevant_tables,
            threshold=config.pipeline.relevance_threshold,
            cached_embedding=cached_embedding
        )

    def _is_uuid_column(self, col: dict, canonical_table: Optional[Any]) -> bool:
        """
        Check if a column is a UUID type.

        Args:
            col: Column info dictionary from database
            canonical_table: Optional canonical schema table

        Returns:
            True if column is UUID type
        """
        col_type = col['type'].upper()

        # Check database type directly
        if 'UUID' in col_type:
            return True

        # Check canonical schema if available
        if canonical_table and col['name'] in canonical_table.columns:
            canonical_col = canonical_table.columns[col['name']]
            canonical_type = canonical_col.data_type.upper()
            if 'UUID' in canonical_type:
                return True

        return False

    def _format_column_line(self, col: dict, canonical_table: Optional[Any]) -> str:
        """
        Format a single column line for schema context.

        Args:
            col: Column info dictionary from database
            canonical_table: Optional canonical schema table

        Returns:
            Formatted column line string
        """
        is_uuid = self._is_uuid_column(col, canonical_table)

        # Build column type and attributes
        col_line = f"  - {col['name']} ({col['type']}"

        if col.get('nullable') is False:
            col_line += ", NOT NULL"
        if col.get('primary_key'):
            col_line += ", PRIMARY KEY"
        if col.get('foreign_keys'):
            col_line += ", FOREIGN KEY"

        # Mark UUID columns for analytics use case
        if is_uuid:
            col_line += ", UUID - for JOINs only, do not SELECT"

        col_line += ")"

        # Add description from canonical schema if available
        if canonical_table and col['name'] in canonical_table.columns:
            description = canonical_table.columns[col['name']].description
            if description and not description.startswith("Column:"):
                col_line += f" - {description}"

        return col_line
    def _expand_tables_via_relationships(self, relevant_tables: list, relevance_scores: dict) -> set:
        """
        OPTIMIZED: Fast FK expansion using pre-computed bidirectional graph.

        Strategy:
        1. Get bidirectional FK graph in ONE pass (O(N) where N = total FKs)
        2. Sort semantic tables by relevance score (expand best matches first)
        3. Add related tables via outbound + inbound FKs using set lookups (O(1))
        4. Hard cap at max_expanded_tables

        Performance: O(K) where K = number of FKs for semantic tables (typically < 30)
        vs. Old: O(S * T) where S = semantic tables, T = total tables
        """
        # Get bidirectional relationships in ONE efficient pass
        outbound_fks, inbound_fks = self.db_toolkit.get_bidirectional_relationships()

        expanded_tables = set(relevant_tables)
        max_tables = config.pipeline.max_expanded_tables

        # Sort by relevance score (expand highest-scoring tables first)
        sorted_tables = sorted(
            relevant_tables,
            key=lambda t: relevance_scores.get(t, 0),
            reverse=True
        )

        logger.info(f"Starting FK expansion from {len(relevant_tables)} tables (max: {max_tables})")

        # Expand in BOTH directions for each semantic table
        for table in sorted_tables:
            if len(expanded_tables) >= max_tables:
                logger.warning(f"Reached max table limit ({max_tables}), stopping expansion")
                break

            # Add outbound relationships (tables this table references)
            # O(1) set lookup instead of O(N) list iteration
            outbound = outbound_fks.get(table, set())
            for related_table in outbound:
                if len(expanded_tables) >= max_tables:
                    break
                # Set.add() is idempotent - duplicates are automatically ignored
                expanded_tables.add(related_table)

            # Add inbound relationships (tables that reference this table)
            # O(1) set lookup instead of O(T) where T = total tables
            inbound = inbound_fks.get(table, set())
            for related_table in inbound:
                if len(expanded_tables) >= max_tables:
                    break
                # Set.add() is idempotent - duplicates are automatically ignored
                expanded_tables.add(related_table)

        if len(expanded_tables) > len(relevant_tables):
            new_tables = expanded_tables - set(relevant_tables)
            logger.info(
                f"FK expansion: {len(relevant_tables)} → {len(expanded_tables)} tables "
                f"(added {len(new_tables)}: {', '.join(sorted(new_tables)[:5])}...)"
            )

        return expanded_tables
    
    def _build_schema_context(self, relevant_tables: list, relevance_scores: dict) -> str:
        """
        Build complete schema context for LLM with relationship expansion.

        Optimization: Only include sample data for semantically matched tables,
        not FK-expanded tables (saves ~300 tokens per table).
        """
        # Track which tables are semantic matches (for sample data)
        semantic_tables = set(relevant_tables)

        # Expand tables to include FK-connected tables (with prioritization)
        expanded_tables = self._expand_tables_via_relationships(relevant_tables, relevance_scores)

        # Format schema for LLM consumption with token budget
        schema_context, token_estimate = self._format_schema_for_llm(
            table_names=list(expanded_tables),
            semantic_tables=semantic_tables
        )

        # Add relevance scores to context
        if relevance_scores:
            score_context = "\n\nTable Relevance Scores:\n"
            for table in relevant_tables[:5]:
                score = relevance_scores.get(table, 0)
                score_context += f"- {table}: {score:.1%} relevant\n"
            schema_context = score_context + "\n" + schema_context

        logger.info(
            f"Schema context: {len(expanded_tables)} tables, "
            f"~{token_estimate:,} tokens (limit: {config.pipeline.max_schema_tokens:,})"
        )

        return schema_context
    
    def _format_schema_for_llm(self, table_names: list, semantic_tables: set) -> tuple[str, int]:
        """
        Format database schema for LLM consumption with token budget tracking.

        Args:
            table_names: List of all tables to include
            semantic_tables: Set of semantically matched tables (get sample data)

        Returns:
            tuple: (schema_context_string, estimated_tokens)

        Speed optimization: Only include sample data for semantic matches,
        not FK-expanded tables. Saves ~300 tokens per expanded table.
        """
        schema_parts = ["Database Schema:"]
        max_tokens = config.pipeline.max_schema_tokens
        current_tokens = 0

        # OPTIMIZATION: Fetch all table info in parallel (major speedup!)
        all_table_info = self.db_toolkit.get_multiple_table_info(table_names)

        for table_name in table_names:
            # Check token budget before adding table
            if current_tokens >= max_tokens:
                remaining_tables = len(table_names) - len(schema_parts) + 1
                logger.warning(
                    f"Token budget ({max_tokens}) reached. "
                    f"Skipping {remaining_tables} remaining tables."
                )
                break

            table_info = all_table_info.get(table_name, {})
            canonical_table = None
            if self.canonical_schema and table_name in self.canonical_schema.tables:
                canonical_table = self.canonical_schema.tables[table_name]

            table_parts = []
            table_parts.append(f"\n## Table: {table_name}")

            # Only include row count if configured and available
            row_count = table_info.get('row_count')
            if row_count is not None:
                table_parts.append(f"Rows: {row_count}")

            if canonical_table:
                table_parts.append(f"Description: {canonical_table.description}")
                if canonical_table.relationships:
                    related = sorted({rel.referenced_table for rel in canonical_table.relationships})
                    if related:
                        table_parts.append(f"Related tables: {', '.join(related)}")

            columns = table_info.get('columns', [])
            if columns:
                table_parts.append("Columns:")
                for col in columns:
                    col_line = self._format_column_line(col, canonical_table)
                    table_parts.append(col_line)

            # SPEED OPTIMIZATION: Only include sample data for semantically matched tables
            # FK-expanded tables get schema only (saves ~300 tokens per table)
            include_samples = (
                config.pipeline.include_sample_data
                and table_name in semantic_tables
            )

            if include_samples:
                # Reuse sample data already fetched in get_multiple_table_info()
                # instead of making another DB call
                sample_data = table_info.get('sample_data', [])
                if sample_data:
                    table_parts.append("Sample data:")
                    for i, row in enumerate(sample_data, 1):
                        table_parts.append(f"  {i}. {row}")

            # Estimate tokens for this table (rough: 1 token ~= 4 characters)
            table_text = "\n".join(table_parts)
            table_tokens = len(table_text) // 4
            current_tokens += table_tokens

            schema_parts.extend(table_parts)

        final_schema = "\n".join(schema_parts)
        final_tokens = len(final_schema) // 4  # Accurate count at end

        return final_schema, final_tokens


# Global instance cache
_analyzer_cache: Dict[tuple, SchemaAnalyzer] = {}


def get_analyzer(
    canonical_schema_path: Optional[str] = None,
    db_toolkit: Optional[GenericDatabaseToolkit] = None,
    query_cache: Optional[Any] = None
) -> SchemaAnalyzer:
    """
    Get or create the analyzer instance (cached by schema path).

    Note: We don't cache by query_cache because it's a shared global instance.

    Args:
        canonical_schema_path: Path to canonical schema
        db_toolkit: Optional database toolkit (for dependency injection)
        query_cache: Optional query cache (shared across pipeline)

    Returns:
        Cached or new SchemaAnalyzer instance
    """
    global _analyzer_cache

    # Use cache key based on canonical_schema_path
    cache_key = (canonical_schema_path,)

    if cache_key not in _analyzer_cache:
        _analyzer_cache[cache_key] = SchemaAnalyzer(
            canonical_schema_path=canonical_schema_path,
            db_toolkit=db_toolkit,
            query_cache=query_cache
        )
    elif query_cache and _analyzer_cache[cache_key].semantic_finder.query_cache != query_cache:
        # Update the query cache if it changed (though it shouldn't in practice)
        _analyzer_cache[cache_key].semantic_finder.query_cache = query_cache

    return _analyzer_cache[cache_key]


def schema_analyzer(state: TextToSQLState) -> Dict[str, Any]:
    """
    Schema analyzer that uses embeddings for semantic table selection.

    For follow-up questions:
    - Uses extracted_query for embedding (table selection)
    - Original query with full history is passed to SQL generator for LLM context
    """
    def create_schema_reasoning_step(tables: list, scores: dict, excel_enhanced: bool = False) -> dict:
        """Create reasoning step for schema analysis."""
        if tables:
            detail = (
                f"Used semantic embeddings to identify {len(tables)} relevant tables. "
                f"Top match: {tables[0]} ({scores.get(tables[0], 0):.1%} similarity)"
            )
            if excel_enhanced:
                detail += " (Enhanced with curated schema metadata)"
            return create_success_step("Schema Analysis", detail)
        else:
            return create_warning_step("Schema Analysis", "No relevant tables found for the query.")

    query = state["original_query"]

    # Use query_for_embedding for table selection
    # This may be the extracted query or a rewritten version (for follow-ups)
    # Cache lookup node handles the rewriting logic
    query_for_embedding = state.get("query_for_embedding") or state.get("extracted_query") or query

    # Resolve canonical schema path
    resolved_path = _resolve_schema_path(state.get("canonical_schema_path"))
    canonical_schema_path = str(resolved_path) if resolved_path else None

    # Get cached embedding if available (from partial cache hit)
    cached_embedding = state.get("cached_embedding")

    # Get query cache from state (initialized by cache_lookup node)
    query_cache = state.get("query_cache")

    try:
        # Measure schema analysis time
        start_time = time.time()

        # Analyze schema using embeddings (use cached embedding if available)
        # Use extracted_query for embedding to ensure consistency
        analyzer = get_analyzer(
            canonical_schema_path=canonical_schema_path,
            query_cache=query_cache
        )
        analysis_result = analyzer.analyze_schema(
            query=query_for_embedding,  # Use extracted query for embedding/table selection
            cached_embedding=cached_embedding
        )

        schema_analysis_time_ms = (time.time() - start_time) * 1000
        
        # Check if schema analysis found an error
        if "schema_analysis_error" in analysis_result:
            return {
                "schema_analysis_error": analysis_result["schema_analysis_error"],
                "schema_analysis_time_ms": schema_analysis_time_ms,
                "reasoning_log": analysis_result.get("reasoning_log", []),
                "schema_overview": get_schema_overview(canonical_schema_path)
            }
        
        # Extract results for successful analysis
        schema_context = analysis_result["schema_context"]
        relevance_scores = analysis_result.get("relevance_scores", {})
        relevant_tables = list(relevance_scores.keys()) if relevance_scores else []

        # Create reasoning step (indicate if Excel-enhanced)
        metadata_enhanced = analyzer.canonical_schema is not None
        reasoning_step = create_schema_reasoning_step(relevant_tables, relevance_scores, metadata_enhanced)

        return {
            "schema_context": schema_context,
            "relevance_scores": relevance_scores,
            "schema_analysis_time_ms": schema_analysis_time_ms,
            "reasoning_log": [reasoning_step],
            "canonical_schema_path": canonical_schema_path,
            "canonical_schema": analyzer.canonical_schema
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Schema Analyzer error: {error_msg}")
        if query:
            logger.debug(f"Query context: {query[:200]}...")
        return {
            "schema_analysis_error": error_msg,
            "reasoning_log": [],
            "error": error_msg,
            "schema_overview": get_schema_overview(canonical_schema_path)
        }
