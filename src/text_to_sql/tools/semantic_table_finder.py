"""
Semantic table finder using sentence-transformers.
Finds relevant tables using semantic similarity with human-provided descriptions from Excel.
"""
import logging
import os
from typing import List, Tuple, Dict, Optional, TYPE_CHECKING
import numpy as np
from sentence_transformers import SentenceTransformer

from .database_toolkit import db_toolkit
from ...common.stores.embedding_store import create_embedding_store, EmbeddingStore

if TYPE_CHECKING:
    from src.schema_ingestion.canonical import CanonicalSchema

logger = logging.getLogger(__name__)


class SemanticTableFinder:
    """
    Find semantically relevant tables using sentence embeddings.

    Uses CanonicalSchema for enhanced table descriptions or falls back to database introspection.
    """

    def __init__(
        self,
        engine,
        model_name: str = "all-mpnet-base-v2",
        cache_dir: str = ".embeddings_cache",
        canonical_schema: Optional['CanonicalSchema'] = None,
        embedding_store: Optional[EmbeddingStore] = None
    ):
        """
        Initialize with sentence transformer model.

        Args:
            engine: Database engine (kept for compatibility)
            model_name: Name of the sentence transformer model
            cache_dir: Directory to cache embeddings (for local file store)
            canonical_schema: Optional canonical schema (preferred)
            embedding_store: Optional pre-configured embedding store (pgvector or local file)
        """
        # Note: engine parameter kept for compatibility but not used
        self.model = SentenceTransformer(model_name)
        self.canonical_schema = canonical_schema

        # Determine namespace for embedding isolation
        if canonical_schema:
            self.namespace = canonical_schema.get_embedding_namespace()
            logger.info(f"Using embedding namespace: {self.namespace}")
        else:
            self.namespace = "default"

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

        logger.info(f"SemanticTableFinder initialized with model: {model_name}, namespace: {self.namespace}")

    def _embeddings_exist(self) -> bool:
        """Check if embeddings already exist in cache for this namespace."""
        try:
            # Try to get one table's embedding to verify cache exists
            table_names = db_toolkit.get_table_names()
            if not table_names:
                return False

            # Check if first table has cached embedding
            first_table = table_names[0]
            embedding = self.embedding_store.get_embedding(first_table, namespace=self.namespace)
            return embedding is not None
        except Exception as e:
            logger.debug(f"Error checking embeddings cache: {e}")
            return False

    def build_embeddings(self) -> None:
        """Build embeddings for all database tables and store them."""
        logger.info("Building table embeddings...")

        for table_name in db_toolkit.get_table_names():
            description = self._create_table_description(table_name)
            embedding = self.model.encode(description)

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
    
    def find_relevant_tables(self, query: str, max_tables: int, threshold: float) -> List[Tuple[str, float, str]]:
        """
        Find tables relevant to query using semantic similarity.

        Returns: List of (table_name, similarity_score, description)
        """
        # Get query embedding
        query_embedding = self.model.encode(query)

        # Search for similar tables using embedding store
        # The store handles the similarity computation (in-database for pgvector)
        similar_tables = self.embedding_store.search_similar(
            query_embedding=query_embedding,
            namespace=self.namespace,
            limit=max_tables,
            min_similarity=threshold
        )

        # Format results: (table_name, similarity_score, description)
        results = []
        for table_name, similarity in similar_tables:
            # Get description from cache or create it
            if table_name not in self.table_descriptions:
                self.table_descriptions[table_name] = self._create_table_description(table_name)
            description = self.table_descriptions[table_name]
            results.append((table_name, similarity, description))

        logger.info(f"Found {len(results)} relevant tables for query (threshold: {threshold})")
        return results
    
    def _create_table_description(self, table_name: str) -> str:
        """
        Create text description of table for embedding - focus on semantic meaning.

        Priority order for descriptions:
        1. CanonicalSchema (LLM/human-provided descriptions) - HIGHEST PRIORITY
        2. Auto-generated from database reflection (fallback)
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

        # Priority 2: Fall back to database reflection only
        # Simple description based on table name
        parts = [f"Table: {table_name}"]

        # Get table info from database
        table_info = db_toolkit.get_table_info(table_name)

        # Add column names with semantic meaning
        if table_info.get('columns'):
            column_names = [col['name'] for col in table_info['columns']]
            # Group columns by semantic meaning
            key_columns = [col for col in column_names if any(keyword in col.lower()
                          for keyword in ['usage', 'memory', 'cpu', 'utilization', 'performance',
                                        'health', 'status', 'datacenter', 'location', 'time',
                                        'rate', 'bandwidth', 'response', 'error', 'latency'])]
            if key_columns:
                parts.append(f"Key metrics: {', '.join(key_columns)}")
            parts.append(f"All columns: {', '.join(column_names)}")

        # Add sample data for semantic context
        sample_data = db_toolkit.get_sample_data(table_name, limit=2)
        if sample_data:
            sample_parts = []
            for row in sample_data:
                # Include actual values for semantic understanding
                row_text = ", ".join([f"{k}: {v}" for k, v in row.items() if v is not None])
                sample_parts.append(row_text)
            parts.append(f"Sample data: {'; '.join(sample_parts)}")

        return ". ".join(parts)
