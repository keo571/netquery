"""
Domain-agnostic SQLAlchemy database toolkit.
Works automatically with any database schema through reflection.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from sqlalchemy import text

from ...common.database.engine import get_engine, get_metadata
from ...common.config import config

logger = logging.getLogger(__name__)


class GenericDatabaseToolkit:
    """Database toolkit using SQLAlchemy reflection."""

    def __init__(self, canonical_schema=None):
        """Initialize generic database toolkit."""
        self._engine = None
        self._initialized = False
        # Cache for outbound FK graph (pre-built at app startup via AppContext)
        self._relationship_cache: Optional[Dict[str, set]] = None
        # Canonical schema - single source of truth for FK relationships
        self._canonical_schema = canonical_schema
    
    @property
    def engine(self):
        """Lazy-load database engine."""
        if not self._initialized:
            self._engine = get_engine()
            if not self.test_connection():
                raise RuntimeError("Database connection failed during initialization")
            logger.info("Database connection established successfully")
            self._initialized = True
        return self._engine
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """Execute SQL query with timeout."""
        start_time = time.time()
        timeout_seconds = config.pipeline.query_timeout_seconds

        def _execute():
            """Execute the query in a separate thread."""
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))

                if result.returns_rows:
                    rows = result.fetchall()
                    results = [dict(row._mapping) for row in rows]
                    row_count = len(results)
                else:
                    results = []
                    row_count = result.rowcount

                return results, row_count

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_execute)

                try:
                    results, row_count = future.result(timeout=timeout_seconds)
                    execution_time_ms = (time.time() - start_time) * 1000

                    return {
                        "success": True,
                        "data": results,
                        "execution_time_ms": execution_time_ms,
                        "row_count": row_count,
                        "truncated": False,
                        "error": None
                    }

                except TimeoutError:
                    execution_time_ms = (time.time() - start_time) * 1000
                    timeout_msg = f"Database query timed out after {timeout_seconds} seconds"
                    print(f"      ⏱️ DATABASE_TIMEOUT ({timeout_seconds:.1f}s) - {timeout_msg}")

                    return {
                        "success": False,
                        "data": None,
                        "execution_time_ms": execution_time_ms,
                        "row_count": 0,
                        "truncated": False,
                        "error": timeout_msg
                    }

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Database Query Execution failed: {error_msg}")
            logger.debug(f"SQL: {sql_query[:500]}...")
            return {
                "success": False,
                "data": None,
                "error": error_msg,
                "operation": "Database Query Execution",
                "execution_time_ms": execution_time_ms,
                "row_count": 0,
                "truncated": False
            }
    
    def get_table_names(self) -> List[str]:
        """Get all table names from the database."""
        metadata = get_metadata()
        return list(metadata.tables.keys())
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get table column names only (for drift detection).

        Used ONLY at startup for validating canonical schema against database.
        SQL generation uses canonical schema exclusively - no DB introspection.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table_name and columns (names only)
        """
        metadata = get_metadata()
        if table_name not in metadata.tables:
            return {"error": f"Table '{table_name}' not found"}

        table = metadata.tables[table_name]

        # Get column names only (for drift detection)
        columns = [{'name': column.name} for column in table.columns]

        return {
            "table_name": table_name,
            "columns": columns,
        }
    
    def get_multiple_table_info(self, table_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        DEPRECATED: Returns empty dict - not used for SQL generation.

        SQL generation now uses canonical schema exclusively.
        This method exists only to avoid breaking existing code.
        Will be removed in future cleanup.

        Returns:
            Empty dict (canonical schema is used instead)
        """
        logger.warning("get_multiple_table_info is deprecated - SQL generation uses canonical schema")
        return {}
    
    def get_table_relationships(self) -> Dict[str, List[str]]:
        """
        Get table relationships via foreign keys (outbound only).
        Returns: Dict[table_name, List[referenced_tables]]
        """
        metadata = get_metadata()
        relationships = {}

        for table_name, table in metadata.tables.items():
            related_tables = []

            for column in table.columns:
                for fk in column.foreign_keys:
                    referenced_table = fk.column.table.name
                    if referenced_table not in related_tables:
                        related_tables.append(referenced_table)

            if related_tables:
                relationships[table_name] = related_tables

        return relationships

    def set_canonical_schema(self, canonical_schema):
        """
        Set canonical schema for FK fallback.
        Call this after initialization if canonical schema becomes available.
        """
        self._canonical_schema = canonical_schema
        # Clear cache since FK source may change
        self._relationship_cache = None

    def get_outbound_relationships(self, use_cache: bool = True) -> Dict[str, set]:
        """
        Get outbound FK relationships from canonical schema.

        Only uses relationships defined in canonical schema - does not query database.
        This is the single source of truth for table relationships.

        Args:
            use_cache: If True (default), return cached graph if available.
                      Set to False to force rebuild (e.g., after schema changes).

        Returns:
            Dict[table_name, set of referenced tables]
            - outbound[table] = set of tables this table references via FK

        Performance: O(N) where N = total FKs in canonical schema, computed once and cached.
        """
        # Return cached graph if available
        if use_cache and self._relationship_cache is not None:
            return self._relationship_cache

        logger.info("Building outbound FK relationship graph from canonical schema...")
        start_time = time.time()

        outbound = self._get_fks_from_canonical_schema()
        fk_count = sum(len(refs) for refs in outbound.values())

        # Cache the result
        self._relationship_cache = outbound

        build_time_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Built FK graph: {fk_count} relationships in {build_time_ms:.1f}ms (cached)"
        )

        return outbound

    def _get_fks_from_canonical_schema(self) -> Dict[str, set]:
        """
        Get outbound FK relationships from canonical schema (JSON file).
        Used when database has no FK constraints (common in production).
        """
        outbound = {}  # table -> set of tables it references

        if not self._canonical_schema:
            logger.warning("No canonical schema available for FK fallback")
            return outbound

        # Iterate through all tables in canonical schema
        for table_name, table_schema in self._canonical_schema.tables.items():
            # Process relationships (foreign keys)
            for relationship in table_schema.relationships:
                referenced_table = relationship.referenced_table

                # Add outbound relationship
                if table_name not in outbound:
                    outbound[table_name] = set()
                outbound[table_name].add(referenced_table)

        return outbound

    def clear_relationship_cache(self) -> None:
        """
        Clear the cached FK relationship graph.
        Call this if the database schema changes (e.g., during migrations).
        """
        self._relationship_cache = None
        logger.info("Cleared FK relationship cache")

    def clear_all_caches(self) -> None:
        """
        Clear all caches (relationships only).
        Call this after schema migrations or database structure changes.
        """
        self.clear_relationship_cache()
        logger.info("Cleared all caches")


# ============================================================================
# FACTORY FUNCTION (Dependency Injection Pattern)
# ============================================================================

_default_toolkit_instance: Optional[GenericDatabaseToolkit] = None


def get_db_toolkit(canonical_schema=None) -> GenericDatabaseToolkit:
    """
    Get or create the default database toolkit instance.

    This factory function enables dependency injection while maintaining
    backward compatibility with code that expects a default instance.

    Args:
        canonical_schema: Optional canonical schema for FK fallback

    Returns:
        GenericDatabaseToolkit instance

    Usage:
        # Get default instance
        toolkit = get_db_toolkit()

        # Or inject into classes
        analyzer = SchemaAnalyzer(schema_path, db_toolkit=get_db_toolkit())
    """
    global _default_toolkit_instance

    if _default_toolkit_instance is None:
        _default_toolkit_instance = GenericDatabaseToolkit(canonical_schema=canonical_schema)

    # Update canonical schema if provided and different
    if canonical_schema is not None and _default_toolkit_instance._canonical_schema != canonical_schema:
        _default_toolkit_instance.set_canonical_schema(canonical_schema)

    return _default_toolkit_instance


def create_db_toolkit(canonical_schema=None) -> GenericDatabaseToolkit:
    """
    Create a NEW database toolkit instance (not the default singleton).

    Use this when you need a separate instance (e.g., for testing,
    or connecting to a different database).

    Args:
        canonical_schema: Optional canonical schema for FK fallback

    Returns:
        New GenericDatabaseToolkit instance
    """
    return GenericDatabaseToolkit(canonical_schema=canonical_schema)