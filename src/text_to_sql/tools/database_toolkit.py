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
        # Cache for bidirectional FK graph (built once on first query)
        self._relationship_cache: Optional[tuple[Dict[str, set], Dict[str, set]]] = None
        # Canonical schema for FK fallback (when DB has no FK constraints)
        self._canonical_schema = canonical_schema
        # Cache for row counts (table scans are expensive)
        self._row_count_cache: Dict[str, int] = {}
    
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
    
    def get_table_info(self, table_name: str, include_row_count: bool = True,
                       include_sample_data: bool = True) -> Dict[str, Any]:
        """
        Get table information including columns, optional row count, and optional sample data.

        Args:
            table_name: Name of the table
            include_row_count: Whether to fetch row count (requires COUNT(*) query)
            include_sample_data: Whether to fetch sample data (requires SELECT query)

        Returns:
            Dictionary with table information
        """
        metadata = get_metadata()
        if table_name not in metadata.tables:
            return {"error": f"Table '{table_name}' not found"}

        table = metadata.tables[table_name]

        # Get column information (from cached metadata, no DB call)
        columns = []
        for column in table.columns:
            col_info = {
                'name': column.name,
                'type': str(column.type),
                'nullable': column.nullable,
                'primary_key': column.primary_key,
                'foreign_keys': []
            }

            # Add foreign key info
            for fk in column.foreign_keys:
                col_info['foreign_keys'].append({
                    'references_table': fk.column.table.name,
                    'references_column': fk.column.name
                })

            columns.append(col_info)

        result = {
            "table_name": table_name,
            "columns": columns,
        }

        # Optional: Add row count (DB call: SELECT COUNT(*))
        if include_row_count:
            result["row_count"] = self._get_row_count(table_name)
        else:
            result["row_count"] = None

        # Optional: Add sample data (DB call: SELECT * LIMIT N)
        if include_sample_data:
            result["sample_data"] = self.get_sample_data(table_name, limit=3)
        else:
            result["sample_data"] = []

        return result
    
    def _get_row_count(self, table_name: str, use_cache: bool = True) -> Optional[int]:
        """
        Get row count for table with caching.

        Args:
            table_name: Name of the table
            use_cache: If True, use cached count if available (default)

        Returns:
            Row count or None if failed

        Performance: Cached row counts avoid expensive COUNT(*) queries.
        """
        # Check cache first
        if use_cache and table_name in self._row_count_cache:
            return self._row_count_cache[table_name]

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()

                # Cache the result
                self._row_count_cache[table_name] = count
                return count
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {e}")
            return None
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample data from table."""
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
            return [dict(row._mapping) for row in result]

    def get_multiple_table_info(self, table_names: List[str],
                                include_row_counts: bool = None,
                                include_sample_data: bool = None) -> Dict[str, Dict[str, Any]]:
        """
        Get table info for multiple tables in parallel.

        Args:
            table_names: List of table names to fetch
            include_row_counts: Whether to fetch row counts (uses config default if None)
            include_sample_data: Whether to fetch sample data (uses config default if None)

        Returns:
            Dict mapping table_name -> table_info

        Performance: Parallelizes database queries across tables.
        With row_counts=False, sample_data=False: ~5ms (no DB calls, metadata only)
        With row_counts=True, sample_data=True: ~25ms parallel vs ~80ms sequential
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Use config defaults if not specified
        if include_row_counts is None:
            include_row_counts = config.pipeline.include_row_counts
        if include_sample_data is None:
            include_sample_data = config.pipeline.include_sample_data

        results = {}

        # Use thread pool for parallel database queries
        with ThreadPoolExecutor(max_workers=min(len(table_names), config.pipeline.max_concurrent_table_queries)) as executor:
            # Submit all table info fetches
            future_to_table = {
                executor.submit(self.get_table_info, table_name,
                              include_row_count=include_row_counts,
                              include_sample_data=include_sample_data): table_name
                for table_name in table_names
            }

            # Collect results as they complete
            for future in as_completed(future_to_table):
                table_name = future_to_table[future]
                try:
                    results[table_name] = future.result()
                except Exception as e:
                    logger.error(f"Failed to get info for {table_name}: {e}")
                    results[table_name] = {"error": str(e)}

        return results
    
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
        logger.info("Set canonical schema for FK fallback")

    def get_bidirectional_relationships(self, use_cache: bool = True) -> tuple[Dict[str, set], Dict[str, set]]:
        """
        HYBRID: Get FK relationships from database OR canonical schema.

        Priority:
        1. Database FK constraints (SQLAlchemy reflection) - if available
        2. Canonical schema relationships - fallback for flexibility

        Args:
            use_cache: If True (default), return cached graph if available.
                      Set to False to force rebuild (e.g., after schema changes).

        Returns:
            tuple: (outbound_fks, inbound_fks)
            - outbound_fks[table] = set of tables this table references
            - inbound_fks[table] = set of tables that reference this table

        Performance: O(N) where N = total FKs, computed once and cached.
        Cache is built on first query and reused for all subsequent queries.
        """
        # Return cached graph if available
        if use_cache and self._relationship_cache is not None:
            return self._relationship_cache

        logger.info("Building bidirectional FK relationship graph...")
        start_time = time.time()

        # Try database FKs first (always preferred when available)
        outbound, inbound = self._get_fks_from_database()
        fk_count = sum(len(refs) for refs in outbound.values())

        # Fallback to canonical schema if no database FKs found
        if fk_count == 0 and self._canonical_schema is not None:
            logger.warning(
                "No FK constraints found in database - falling back to canonical schema. "
                "This is common for production databases that avoid FK constraints for flexibility."
            )
            outbound, inbound = self._get_fks_from_canonical_schema()
            fk_count = sum(len(refs) for refs in outbound.values())
            source = "canonical schema"
        else:
            source = "database constraints"

        # Cache the result
        self._relationship_cache = (outbound, inbound)

        build_time_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Built FK graph from {source}: {fk_count} FK relationships "
            f"in {build_time_ms:.1f}ms (cached for reuse)"
        )

        return outbound, inbound

    def _get_fks_from_database(self) -> tuple[Dict[str, set], Dict[str, set]]:
        """
        Get FK relationships from database using SQLAlchemy reflection.
        Returns empty dicts if no FKs found (common in production DBs).
        """
        metadata = get_metadata()
        outbound = {}  # table -> set of tables it references
        inbound = {}   # table -> set of tables that reference it

        # Single pass through all tables and FKs
        for table_name, table in metadata.tables.items():
            for column in table.columns:
                for fk in column.foreign_keys:
                    referenced_table = fk.column.table.name

                    # Add outbound relationship
                    if table_name not in outbound:
                        outbound[table_name] = set()
                    outbound[table_name].add(referenced_table)

                    # Add inbound relationship (reverse direction)
                    if referenced_table not in inbound:
                        inbound[referenced_table] = set()
                    inbound[referenced_table].add(table_name)

        return outbound, inbound

    def _get_fks_from_canonical_schema(self) -> tuple[Dict[str, set], Dict[str, set]]:
        """
        Get FK relationships from canonical schema (JSON file).
        Used when database has no FK constraints (common in production).
        """
        outbound = {}  # table -> set of tables it references
        inbound = {}   # table -> set of tables that reference it

        if not self._canonical_schema:
            logger.warning("No canonical schema available for FK fallback")
            return outbound, inbound

        # Iterate through all tables in canonical schema
        for table_name, table_schema in self._canonical_schema.tables.items():
            # Process relationships (foreign keys)
            for relationship in table_schema.relationships:
                referenced_table = relationship.referenced_table

                # Add outbound relationship
                if table_name not in outbound:
                    outbound[table_name] = set()
                outbound[table_name].add(referenced_table)

                # Add inbound relationship (reverse direction)
                if referenced_table not in inbound:
                    inbound[referenced_table] = set()
                inbound[referenced_table].add(table_name)

        return outbound, inbound

    def clear_relationship_cache(self) -> None:
        """
        Clear the cached FK relationship graph.
        Call this if the database schema changes (e.g., during migrations).
        """
        self._relationship_cache = None
        logger.info("Cleared FK relationship cache")

    def clear_row_count_cache(self) -> None:
        """
        Clear the cached row counts.
        Call this after bulk inserts/deletes or when counts need to be refreshed.
        """
        self._row_count_cache.clear()
        logger.info("Cleared row count cache")

    def clear_all_caches(self) -> None:
        """
        Clear all caches (relationships and row counts).
        Call this after schema migrations or major data changes.
        """
        self.clear_relationship_cache()
        self.clear_row_count_cache()
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
        logger.info("Created default database toolkit instance")

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