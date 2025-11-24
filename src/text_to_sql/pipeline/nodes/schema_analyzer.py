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
                 embedding_store = None,
                 embedding_service = None):
        """
        Initialize the analyzer with embedding support (required).

        Args:
            canonical_schema_path: Path to canonical schema file
            db_toolkit: Database toolkit instance (uses default if None)
            embedding_store: Pre-configured embedding store (avoids creating new one)
            embedding_service: Pre-configured embedding service
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

        # Create semantic finder with provided stores to avoid creating duplicates
        self.semantic_finder = SemanticTableFinder(
            model_name=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
            cache_dir=os.getenv("EMBEDDING_CACHE_DIR", ".embeddings_cache"),
            canonical_schema=self.canonical_schema,
            embedding_store=embedding_store,
            embedding_service=embedding_service
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
            logger.info(f"No relevant tables found for query: {query[:30]}...")
            
            # Get available tables for error message
            all_tables = list(self.semantic_finder.canonical_schema.tables.keys())
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
    
    def _find_relevant_tables(self, query: str):
        """Find tables relevant to the query using embeddings."""
        return self.semantic_finder.find_relevant_tables(
            query=query,
            max_tables=config.pipeline.max_relevant_tables,
            threshold=config.pipeline.relevance_threshold
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

    def _format_column_line_from_canonical(self, col_schema) -> str:
        """
        Format a single column line from canonical schema (pure canonical approach).

        Args:
            col_schema: ColumnSchema object from canonical schema

        Returns:
            Formatted column line string
        """
        # Build column type and attributes from canonical schema
        col_line = f"  - {col_schema.name} ({col_schema.data_type}"

        if not col_schema.is_nullable:
            col_line += ", NOT NULL"

        col_line += ")"

        # Add description
        if col_schema.description and not col_schema.description.startswith("Column:"):
            col_line += f" - {col_schema.description}"

        # Add sample values if available
        if col_schema.sample_values:
            samples_str = ", ".join(str(v) for v in col_schema.sample_values[:5])  # Limit to 5
            col_line += f" (examples: {samples_str})"

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

        # Add relevance scores header if available
        if relevance_scores:
            schema_context = self._add_relevance_scores_header(relevant_tables, relevance_scores) + schema_context

        logger.info(
            f"Schema context: {len(expanded_tables)} tables, "
            f"~{token_estimate:,} tokens (limit: {config.pipeline.max_schema_tokens:,})"
        )

        return schema_context

    def _add_relevance_scores_header(self, relevant_tables: list, relevance_scores: dict) -> str:
        """
        Format relevance scores as context header.

        Args:
            relevant_tables: List of table names
            relevance_scores: Dict mapping table names to relevance scores (0-1)

        Returns:
            Formatted string with top 5 relevance scores
        """
        score_lines = ["\n\nTable Relevance Scores:"]
        for table in relevant_tables[:5]:
            score = relevance_scores.get(table, 0)
            score_lines.append(f"- {table}: {score:.1%} relevant")
        return "\n".join(score_lines) + "\n\n"
    
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

        # PURE CANONICAL SCHEMA APPROACH:
        # All table/column info comes from canonical schema JSON.
        # No database introspection during SQL generation.
        # Drift detection at startup ensures canonical schema matches database.

        for table_name in table_names:
            # Check token budget before adding table
            if current_tokens >= max_tokens:
                remaining_tables = len(table_names) - len(schema_parts) + 1
                logger.warning(
                    f"Token budget ({max_tokens}) reached. "
                    f"Skipping {remaining_tables} remaining tables."
                )
                break

            # Get table schema from canonical schema
            if not self.canonical_schema or table_name not in self.canonical_schema.tables:
                logger.warning(f"Table {table_name} not found in canonical schema, skipping")
                continue

            canonical_table = self.canonical_schema.tables[table_name]

            table_parts = []
            table_parts.append(f"\n## Table: {table_name}")
            table_parts.append(f"Description: {canonical_table.description}")

            # Show explicit JOIN paths to help LLM generate correct SQL
            if canonical_table.relationships:
                table_parts.append("Relationships:")
                for rel in canonical_table.relationships:
                    join_hint = f"  - JOIN {rel.referenced_table} ON {table_name}.{rel.foreign_key_column} = {rel.referenced_table}.{rel.referenced_column}"
                    table_parts.append(join_hint)

            # Add columns from canonical schema
            if canonical_table.columns:
                table_parts.append("Columns:")
                for col_name, col_schema in canonical_table.columns.items():
                    col_line = self._format_column_line_from_canonical(col_schema)
                    table_parts.append(col_line)

            # Estimate tokens for this table (rough: 1 token ~= 4 characters)
            table_text = "\n".join(table_parts)
            table_tokens = len(table_text) // 4
            current_tokens += table_tokens

            schema_parts.extend(table_parts)

        final_schema = "\n".join(schema_parts)
        final_tokens = len(final_schema) // 4  # Accurate count at end

        return final_schema, final_tokens


def get_analyzer(
    canonical_schema_path: Optional[str] = None,
    db_toolkit: Optional[GenericDatabaseToolkit] = None,
    embedding_store = None,
    embedding_service = None
) -> SchemaAnalyzer:
    """
    Get the analyzer instance from AppContext.

    Note: Parameters are kept for backward compatibility but are ignored.
    The analyzer is now managed by AppContext with resources initialized at startup.

    Returns:
        Cached SchemaAnalyzer instance from AppContext
    """
    from ....api.app_context import AppContext
    return AppContext.get_instance().get_schema_analyzer()


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

    try:
        # Measure schema analysis time
        start_time = time.time()

        # Analyze schema using embeddings
        # Use extracted_query for embedding to ensure consistency
        analyzer = get_analyzer(
            canonical_schema_path=canonical_schema_path
        )
        analysis_result = analyzer.analyze_schema(
            query=query_for_embedding  # Use extracted query for embedding/table selection
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
