"""
Application context with singleton pattern for shared resources.

This module provides centralized access to application-wide singleton instances
like caches, database connections, and LLM clients.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class AppContext:
    """
    Singleton application context managing shared resources.

    Eagerly initializes all expensive resources on creation:
    - SQL query cache
    - Schema embedding store
    - Embedding service
    - Database engine
    - LLM client
    - Schema analyzer (loads canonical schema and embeddings)

    All resources are initialized immediately to avoid any query latency.
    """

    _instance: Optional['AppContext'] = None

    def __init__(self):
        """Private constructor. Use get_instance() instead."""
        if AppContext._instance is not None:
            raise RuntimeError("AppContext is a singleton. Use AppContext.get_instance()")

        logger.info("Initializing AppContext singleton with all resources...")

        # Eagerly initialize all resources immediately
        self._initialize_resources()

        logger.info("AppContext singleton initialized successfully")

    def _initialize_resources(self):
        """Initialize all resources immediately."""
        # Import modules here to avoid circular dependencies
        from src.text_to_sql.tools.sql_cache import SQLCache
        from src.common.stores.embedding_store import create_embedding_store
        from src.common.database.engine import get_engine
        from src.text_to_sql.utils.llm_utils import get_llm as get_llm_util
        from src.common.embeddings import EmbeddingService
        from src.text_to_sql.pipeline.nodes.schema_analyzer import get_analyzer
        from src.common.schema_summary import _resolve_schema_path

        # Initialize database engine first
        self._db_engine = get_engine()
        logger.info("Initialized database engine")

        # Initialize embedding service
        model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        self._embedding_service = EmbeddingService(model_name=model_name)
        logger.info(f"Initialized embedding service with model {model_name}")

        # Get schema ID (required for cache isolation)
        schema_id = os.getenv('SCHEMA_ID')
        if not schema_id:
            raise ValueError(
                "SCHEMA_ID environment variable is required for cache isolation. "
                "Set it to your database name (e.g., 'sample', 'neila')"
            )

        # Initialize embedding store
        database_url = os.getenv('EMBEDDING_DATABASE_URL')
        # Derive cache path from schema ID for automatic namespace isolation
        embedding_cache_path = f"data/{schema_id}_embeddings_cache.db"
        self._embedding_store = create_embedding_store(
            database_url=database_url,
            db_path=embedding_cache_path
        )
        logger.info(f"Initialized embedding store: {embedding_cache_path}")

        # Initialize LLM client
        self._llm = get_llm_util()
        logger.info("Initialized LLM client")

        # Initialize SQL cache
        # Derive cache path from schema ID for automatic namespace isolation
        sql_cache_path = f"data/{schema_id}_sql_cache.db"
        self._sql_cache = SQLCache(
            db_path=sql_cache_path,
            enable_fuzzy_fallback=True,
            fuzzy_threshold=0.85
        )
        logger.info(f"Initialized SQL cache: {sql_cache_path}")

        # Initialize schema analyzer
        # Pass embedding store and service to avoid creating duplicates
        canonical_schema_path = _resolve_schema_path()
        if canonical_schema_path:
            self._schema_analyzer = get_analyzer(
                canonical_schema_path=canonical_schema_path,
                embedding_store=self._embedding_store,
                embedding_service=self._embedding_service
            )
            logger.info(f"Initialized schema analyzer (using shared embedding store and service)")

            # Validate schema drift: ensure canonical schema matches actual database
            self._validate_schema_drift()
        else:
            self._schema_analyzer = None
            logger.warning("No canonical schema path configured - schema analyzer not initialized")

    def _validate_schema_drift(self):
        """
        Validate that canonical schema matches actual database schema.

        Checks that all tables and columns defined in the canonical schema
        exist in the actual database. Does NOT require database to have ONLY
        those tables/columns - it's fine if the database has extras.

        Raises:
            ValueError: If any table or column from canonical schema is missing in database
        """
        from src.text_to_sql.tools.database_toolkit import get_db_toolkit

        logger.info("Validating canonical schema against database schema...")

        toolkit = get_db_toolkit()
        canonical_schema = self._schema_analyzer.canonical_schema

        errors = []
        warnings = []

        # Get all actual DB table names
        try:
            db_tables = set(toolkit.get_table_names())
        except Exception as e:
            logger.error(f"Failed to list database tables: {e}")
            raise ValueError(f"Cannot validate schema drift: Failed to connect to database: {e}")

        # Validate each table in canonical schema
        for table_name, table_schema in canonical_schema.tables.items():
            # Check if table exists in database
            if table_name not in db_tables:
                errors.append(f"Table '{table_name}' defined in canonical schema but not found in database")
                continue  # Skip column validation if table doesn't exist

            # Get actual columns from database (column names only)
            try:
                table_info = toolkit.get_table_info(table_name)
                db_columns = {col['name'] for col in table_info.get('columns', [])}
            except Exception as e:
                warnings.append(f"Failed to introspect table '{table_name}': {e}")
                continue

            # Check each column in canonical schema
            for col_name in table_schema.columns.keys():
                if col_name not in db_columns:
                    errors.append(
                        f"Column '{table_name}.{col_name}' defined in canonical schema "
                        f"but not found in database"
                    )

        # Report results
        total_tables = len(canonical_schema.tables)
        total_columns = sum(len(t.columns) for t in canonical_schema.tables.values())

        if errors:
            error_summary = "\n".join([f"  ❌ {err}" for err in errors])
            logger.error(
                f"Schema drift detected ({len(errors)} mismatches):\n{error_summary}\n\n"
                f"Your canonical schema defines tables/columns that don't exist in the database.\n"
                f"Please update the canonical schema or fix the database schema."
            )
            raise ValueError(
                f"Schema drift detected: {len(errors)} table/column mismatches. "
                f"See logs for details."
            )

        if warnings:
            warning_summary = "\n".join([f"  ⚠️  {warn}" for warn in warnings])
            logger.warning(f"Schema validation warnings:\n{warning_summary}")

        logger.info(
            f"✅ Schema validation passed: {total_tables} tables, "
            f"{total_columns} columns validated successfully"
        )

    @classmethod
    def get_instance(cls) -> 'AppContext':
        """Get the singleton instance of AppContext."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        if cls._instance:
            cls._instance.cleanup()
            cls._instance = None
            logger.info("Reset AppContext singleton")

    def get_sql_cache(self):
        """Get the SQL query cache instance (already initialized)."""
        return self._sql_cache

    def get_embedding_store(self):
        """Get the schema embedding store instance (already initialized)."""
        return self._embedding_store

    def get_embedding_service(self):
        """Get the embedding service instance (already initialized)."""
        return self._embedding_service

    def get_db_engine(self):
        """Get the database engine instance (already initialized)."""
        return self._db_engine

    def get_llm(self):
        """Get the LLM client instance (already initialized)."""
        return self._llm

    def get_schema_analyzer(self):
        """Get the schema analyzer instance (already initialized)."""
        return self._schema_analyzer

    def cleanup(self):
        """
        Cleanup resources (close connections, etc.).

        Call this on application shutdown.
        """
        if self._sql_cache:
            try:
                self._sql_cache.close()
                logger.info("Closed SQL cache")
            except Exception as e:
                logger.error(f"Error closing SQL cache: {e}")

        if self._embedding_store:
            try:
                if hasattr(self._embedding_store, 'close'):
                    self._embedding_store.close()
                logger.info("Closed embedding store")
            except Exception as e:
                logger.error(f"Error closing embedding store: {e}")

        if self._db_engine:
            try:
                self._db_engine.dispose()
                logger.info("Disposed database engine")
            except Exception as e:
                logger.error(f"Error disposing database engine: {e}")

        # Reset references
        self._sql_cache = None
        self._embedding_store = None
        self._embedding_service = None
        self._db_engine = None
        self._llm = None
        self._schema_analyzer = None


# Convenience functions for direct access

def initialize_app_context():
    """
    Initialize the AppContext singleton.

    This creates the singleton instance and initializes all resources.
    Call this in your application's startup event handler:
    - FastAPI: lifespan startup
    - Flask: before_first_request or app startup

    All resources are initialized eagerly on first call to get_instance().
    """
    AppContext.get_instance()


def cleanup_app_context():
    """Cleanup all application resources."""
    AppContext.get_instance().cleanup()
