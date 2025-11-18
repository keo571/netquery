"""
Semantic table finder using Gemini embeddings.
Requires curated CanonicalSchema descriptions for all tables.
"""
import logging
import os
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from ...common.stores.embedding_store import create_embedding_store, EmbeddingStore
from ...common.embeddings import EmbeddingService
from .query_embedding_cache import QueryEmbeddingCache

if TYPE_CHECKING:
    from src.schema_ingestion.canonical import CanonicalSchema

logger = logging.getLogger(__name__)


class SemanticTableFinder:
    """Find semantically relevant tables using Gemini embeddings and canonical schema metadata."""

    def __init__(
        self,
        model_name: str = "gemini-embedding-001",
        cache_dir: str = ".embeddings_cache",
        canonical_schema: Optional['CanonicalSchema'] = None,
        embedding_store: Optional[EmbeddingStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        enable_query_cache: bool = True,
        query_cache: Optional[QueryEmbeddingCache] = None,
    ):
        """
        Initialize with Gemini embeddings model.

        Args:
            model_name: Name of the Gemini embedding model
            cache_dir: Directory to cache embeddings (for local file store)
            canonical_schema: Optional canonical schema (preferred)
            embedding_store: Optional pre-configured embedding store (pgvector or local file)
            embedding_service: Optional embedding service override (defaults to Gemini embeddings)
            enable_query_cache: Enable SQLite caching of query embeddings (default: True)
            query_cache: Optional pre-initialized query cache (if None, creates new one)
        """
        self.embedding_service = embedding_service or EmbeddingService(model_name=model_name)
        self.model_name = model_name
        self.canonical_schema = canonical_schema

        # Initialize query embedding cache (normalization + fuzzy matching)
        self.query_cache = query_cache  # Use provided cache if available
        if self.query_cache is None and enable_query_cache:
            cache_db_path = os.path.join(cache_dir, "query_cache.db")
            self.query_cache = QueryEmbeddingCache(
                db_path=cache_db_path,
                enable_fuzzy_fallback=True,  # Two-tier matching
                fuzzy_threshold=0.85
            )
            logger.info(f"Query embedding cache (normalization + fuzzy) enabled at {cache_db_path}")
        elif self.query_cache:
            logger.info(f"Using provided query cache instance")

        # Determine namespace for embedding isolation
        if canonical_schema:
            self.namespace = canonical_schema.get_embedding_namespace()
            logger.info(f"Using embedding namespace: {self.namespace}")
        else:
            raise ValueError(
                "SemanticTableFinder requires a canonical schema with table and column descriptions."
            )

        env_namespace = os.getenv("SCHEMA_ID")
        if env_namespace:
            self.namespace = env_namespace

        # Create or use provided embedding store
        if embedding_store:
            self.embedding_store = embedding_store
            logger.info(f"Using provided embedding store: {type(embedding_store).__name__}")
        else:
            # Auto-detect: PostgreSQL pgvector or local file cache
            database_url = os.getenv('EMBEDDING_DATABASE_URL')
            self.embedding_store = create_embedding_store(
                database_url=database_url,
                cache_dir=cache_dir
            )
            logger.info(f"Created embedding store: {type(self.embedding_store).__name__}")

        # Cache for in-memory lookups (for performance)
        self.table_descriptions: Dict[str, str] = {}

        logger.info(
            "SemanticTableFinder initialized with Gemini model: %s, namespace: %s",
            self.model_name,
            self.namespace
        )

    def build_embeddings(self) -> None:
        """Build embeddings for all database tables and store them."""
        logger.info("Building table embeddings...")

        for table_name in self.canonical_schema.tables:
            description = self._create_table_description(table_name)
            embedding = self.embedding_service.embed_text(description)

            # Store in embedding store
            self.embedding_store.store(
                table_name=table_name,
                description=description,
                embedding=embedding,
                namespace=self.namespace
            )

            # Cache description for in-memory lookups
            self.table_descriptions[table_name] = description

        logger.info(f"Built embeddings for {len(self.table_descriptions)} tables")
    
    def find_relevant_tables(
        self,
        query: str,
        max_tables: int,
        threshold: float,
        cached_embedding: Optional[List[float]] = None
    ) -> List[Tuple[str, float]]:
        """
        Find tables relevant to query using semantic similarity.

        Args:
            query: Natural language query
            max_tables: Maximum number of tables to return
            threshold: Minimum similarity threshold
            cached_embedding: Pre-computed embedding (if available from cache)

        Returns: List of (table_name, similarity_score)
        """
        # Get query embedding (with caching if enabled)
        if cached_embedding:
            # Use the provided cached embedding (from partial cache hit)
            query_embedding = cached_embedding
            logger.info("Using cached embedding from partial cache hit")
        elif self.query_cache:
            # Check cache and potentially generate new embedding
            embedding, cached_sql = self.query_cache.get_or_create(
                query,
                lambda q: self.embedding_service.embed_query(q)
            )
            query_embedding = embedding
        else:
            # No cache - generate embedding directly
            query_embedding = self.embedding_service.embed_query(query)

        # Search for similar tables using embedding store
        # The store handles the similarity computation (in-database for pgvector)
        similar_tables = self.embedding_store.search_similar(
            query_embedding=query_embedding,
            namespace=self.namespace,
            limit=max_tables,
            min_similarity=threshold
        )

        # Format results: (table_name, similarity_score)
        # Note: We don't return descriptions since they're not used by callers
        results = [(table_name, similarity) for table_name, similarity in similar_tables]

        logger.info(f"Found {len(results)} relevant tables for query (threshold: {threshold})")
        return results
    
    def _create_table_description(self, table_name: str) -> str:
        """
        Create text description of table for embedding - focus on semantic meaning.

        Requires CanonicalSchema (LLM/human-provided descriptions).
        """
        # Priority 1: Use CanonicalSchema (preferred)
        if self.canonical_schema and table_name in self.canonical_schema.tables:
            table_schema = self.canonical_schema.tables[table_name]

            # Start with canonical description (from LLM or human)
            parts = [f"Table: {table_name} - {table_schema.description}"]

            # Add column descriptions
            if table_schema.columns:
                col_descs = []
                for col_name, col in table_schema.columns.items():
                    col_desc = col.description
                    # Only include if not placeholder
                    if col_desc and not col_desc.startswith("Column:"):
                        col_descs.append(f"{col_name}: {col_desc}")
                    else:
                        col_descs.append(col_name)

                if col_descs:
                    parts.append(f"Columns: {', '.join(col_descs)}")

            # Add relationship context
            if table_schema.relationships:
                related = [rel.referenced_table for rel in table_schema.relationships]
                parts.append(f"Related to: {', '.join(related)}")

            logger.debug(f"Using canonical schema description for {table_name}")
            return ". ".join(parts)

        raise KeyError(
            f"Table '{table_name}' is missing from the canonical schema. Ensure all tables include descriptions."
        )
