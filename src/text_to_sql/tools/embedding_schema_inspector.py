"""
Embedding-based schema inspector using sentence-transformers.
Finds relevant tables using semantic similarity instead of keyword matching.
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import json
import os
from pathlib import Path

# Require sentence-transformers - no fallbacks
from sentence_transformers import SentenceTransformer

from sqlalchemy import inspect, MetaData, Table
from sqlalchemy.engine import Engine

from .database_toolkit import DatabaseToolkit

logger = logging.getLogger(__name__)


@dataclass
class TableEmbedding:
    """Store table information with its embedding."""
    table_name: str
    description: str
    columns: List[str]
    column_types: Dict[str, str]
    sample_data: Optional[List[Dict]] = None
    embedding: Optional[np.ndarray] = None
    foreign_keys: Optional[List[Dict]] = None
    indexes: Optional[List[str]] = None


class EmbeddingSchemaInspector:
    """
    Use sentence embeddings to find semantically relevant tables for queries.
    Requires sentence-transformers to be installed - no keyword fallbacks.
    """
    
    def __init__(self, 
                 engine: Engine,
                 model_name: str = "all-mpnet-base-v2",
                 cache_dir: str = ".embeddings_cache"):
        """
        Initialize the embedding-based schema inspector.
        
        Args:
            engine: SQLAlchemy engine
            model_name: Sentence transformer model to use
            cache_dir: Directory to cache embeddings
        """
        self.engine = engine
        self.metadata = MetaData()
        self.metadata.reflect(bind=engine)
        self.inspector = inspect(engine)
        
        # Initialize embedding model (required)
        self.model = SentenceTransformer(model_name)
        logger.info(f"Loaded embedding model: {model_name}")
                
        # Cache directory for embeddings
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Store table embeddings
        self.table_embeddings: Dict[str, TableEmbedding] = {}
        
        # Initialize embeddings for all tables
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Create embeddings for all tables in the database."""
        cache_file = self.cache_dir / f"{self.engine.url.database}_embeddings.json"
        
        # Try to load from cache
        if cache_file.exists():
            try:
                self._load_embeddings_from_cache(cache_file)
                logger.info(f"Loaded embeddings from cache: {cache_file}")
                return
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        
        # Create embeddings for each table
        for table_name in self.metadata.tables:
            table = self.metadata.tables[table_name]
            table_embedding = self._create_table_embedding(table_name, table)
            self.table_embeddings[table_name] = table_embedding
        
        # Save to cache
        self._save_embeddings_to_cache(cache_file)
        logger.info(f"Saved embeddings to cache: {cache_file}")
    
    def _create_table_embedding(self, table_name: str, table: Table) -> TableEmbedding:
        """
        Create an embedding for a single table.
        
        Args:
            table_name: Name of the table
            table: SQLAlchemy Table object
        
        Returns:
            TableEmbedding object with metadata and embedding
        """
        # Extract column information
        columns = [col.name for col in table.columns]
        column_types = {col.name: str(col.type) for col in table.columns}
        
        # Get foreign keys
        foreign_keys = []
        try:
            fks = self.inspector.get_foreign_keys(table_name)
            for fk in fks:
                foreign_keys.append({
                    'columns': fk['constrained_columns'],
                    'referred_table': fk['referred_table'],
                    'referred_columns': fk['referred_columns']
                })
        except Exception as e:
            logger.debug(f"Could not get foreign keys for {table_name}: {e}")
        
        # Get indexes
        indexes = []
        try:
            idx_list = self.inspector.get_indexes(table_name)
            indexes = [idx['name'] for idx in idx_list if idx['name']]
        except Exception as e:
            logger.debug(f"Could not get indexes for {table_name}: {e}")
        
        # Create description for embedding
        description = self._create_table_description(
            table_name, columns, column_types, foreign_keys
        )
        
        # Get sample data (limit to 3 rows for context)
        sample_data = None
        try:
            toolkit = DatabaseToolkit(self.engine.url.render_as_string(hide_password=False))
            result = toolkit.execute_query(f"SELECT * FROM {table_name} LIMIT 3")
            if result['success'] and result['data']:
                sample_data = result['data']
        except Exception as e:
            logger.debug(f"Could not get sample data for {table_name}: {e}")
        
        # Create embedding
        try:
            # Include sample data in embedding context if available
            embedding_text = description
            if sample_data:
                # Add sample values to context (just values, not full rows)
                sample_values = []
                for row in sample_data[:2]:  # Use max 2 rows
                    sample_values.extend([str(v) for v in row.values() if v])
                if sample_values:
                    embedding_text += f" Sample values: {' '.join(sample_values[:20])}"
            
            embedding = self.model.encode(embedding_text)
        except Exception as e:
            logger.error(f"Failed to create embedding for {table_name}: {e}")
            # If embedding fails, this is a critical error since we don't have fallbacks
            raise RuntimeError(f"Embedding creation failed for {table_name}: {e}")
        
        return TableEmbedding(
            table_name=table_name,
            description=description,
            columns=columns,
            column_types=column_types,
            sample_data=sample_data,
            embedding=embedding,
            foreign_keys=foreign_keys,
            indexes=indexes
        )
    
    def _create_table_description(self, 
                                  table_name: str, 
                                  columns: List[str],
                                  column_types: Dict[str, str],
                                  foreign_keys: List[Dict]) -> str:
        """
        Create a natural language description of a table for embedding.
        
        Args:
            table_name: Name of the table
            columns: List of column names
            column_types: Dictionary of column types
            foreign_keys: List of foreign key relationships
        
        Returns:
            Natural language description
        """
        # Parse table name (handle snake_case)
        table_words = table_name.replace('_', ' ')
        
        # Build description
        parts = [f"Table {table_words}"]
        
        # Add column context
        column_desc = []
        for col in columns:
            col_words = col.replace('_', ' ')
            col_type = column_types.get(col, 'unknown')
            
            # Add semantic hints based on column names
            if 'id' in col.lower():
                column_desc.append(f"{col_words} identifier")
            elif 'name' in col.lower():
                column_desc.append(f"{col_words} name")
            elif 'date' in col.lower() or 'time' in col.lower():
                column_desc.append(f"{col_words} timestamp")
            elif 'status' in col.lower():
                column_desc.append(f"{col_words} status")
            elif 'count' in col.lower() or 'num' in col.lower():
                column_desc.append(f"{col_words} count number")
            elif 'price' in col.lower() or 'cost' in col.lower() or 'amount' in col.lower():
                column_desc.append(f"{col_words} monetary amount")
            elif 'percent' in col.lower() or 'rate' in col.lower():
                column_desc.append(f"{col_words} percentage rate")
            elif 'ip' in col.lower() or 'address' in col.lower():
                column_desc.append(f"{col_words} network address")
            elif 'cpu' in col.lower() or 'memory' in col.lower() or 'disk' in col.lower():
                column_desc.append(f"{col_words} resource metric")
            else:
                column_desc.append(col_words)
        
        parts.append(f"with columns: {', '.join(column_desc)}")
        
        # Add relationship context
        if foreign_keys:
            relationships = []
            for fk in foreign_keys:
                ref_table = fk['referred_table'].replace('_', ' ')
                relationships.append(f"related to {ref_table}")
            parts.append(f"relationships: {', '.join(relationships)}")
        
        # Add domain-specific context for network infrastructure
        if any(term in table_name.lower() for term in ['load_balancer', 'lb', 'balancer']):
            parts.append("network load balancing traffic distribution")
        elif any(term in table_name.lower() for term in ['server', 'backend', 'node']):
            parts.append("backend server infrastructure compute nodes")
        elif any(term in table_name.lower() for term in ['vip', 'virtual_ip']):
            parts.append("virtual IP addresses network endpoints")
        elif any(term in table_name.lower() for term in ['metric', 'monitor', 'stats']):
            parts.append("performance metrics monitoring statistics")
        elif any(term in table_name.lower() for term in ['ssl', 'cert', 'tls']):
            parts.append("SSL TLS certificates security encryption")
        elif any(term in table_name.lower() for term in ['datacenter', 'dc', 'zone']):
            parts.append("datacenter region zone location infrastructure")
        
        return ' '.join(parts)
    
    def find_relevant_tables(self, 
                            query: str, 
                            top_k: int = 5,
                            threshold: float = 0.3) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Find the most relevant tables for a given query using semantic similarity.
        
        Args:
            query: Natural language query
            top_k: Number of top tables to return
            threshold: Minimum similarity threshold (0-1)
        
        Returns:
            List of tuples (table_name, similarity_score, metadata)
        """
        # Embedding model is required - no fallbacks
        try:
            # Create query embedding
            query_embedding = self.model.encode(query)
            
            # Calculate similarities
            similarities = []
            for table_name, table_emb in self.table_embeddings.items():
                if table_emb.embedding is not None:
                    # Cosine similarity
                    similarity = self._cosine_similarity(query_embedding, table_emb.embedding)
                    
                    if similarity >= threshold:
                        metadata = {
                            'columns': table_emb.columns,
                            'column_types': table_emb.column_types,
                            'foreign_keys': table_emb.foreign_keys,
                            'indexes': table_emb.indexes,
                            'description': table_emb.description
                        }
                        similarities.append((table_name, similarity, metadata))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Log results for debugging
            logger.info(f"Query: '{query}'")
            logger.info(f"Top relevant tables:")
            for table, score, _ in similarities[:top_k]:
                logger.info(f"  - {table}: {score:.3f}")
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            # No fallbacks - if embeddings fail, the system should fail gracefully
            raise RuntimeError(f"Embedding search failed: {e}")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    
    def get_related_tables(self, table_name: str) -> List[str]:
        """
        Get tables related through foreign keys.
        
        Args:
            table_name: Name of the table
        
        Returns:
            List of related table names
        """
        related = set()
        
        if table_name in self.table_embeddings:
            table_emb = self.table_embeddings[table_name]
            
            # Tables this table references
            if table_emb.foreign_keys:
                for fk in table_emb.foreign_keys:
                    related.add(fk['referred_table'])
            
            # Tables that reference this table
            for other_table, other_emb in self.table_embeddings.items():
                if other_emb.foreign_keys:
                    for fk in other_emb.foreign_keys:
                        if fk['referred_table'] == table_name:
                            related.add(other_table)
        
        return list(related)
    
    def explain_table_relevance(self, query: str, table_name: str) -> str:
        """
        Explain why a table is relevant to a query.
        
        Args:
            query: Natural language query
            table_name: Name of the table
        
        Returns:
            Explanation string
        """
        if table_name not in self.table_embeddings:
            return f"Table {table_name} not found"
        
        table_emb = self.table_embeddings[table_name]
        query_lower = query.lower()
        
        reasons = []
        
        # Check table name match
        if any(word in table_name.lower() for word in query_lower.split()):
            reasons.append(f"Table name '{table_name}' matches query terms")
        
        # Check column matches
        matching_cols = []
        for col in table_emb.columns:
            if any(word in col.lower() for word in query_lower.split()):
                matching_cols.append(col)
        
        if matching_cols:
            reasons.append(f"Columns match query: {', '.join(matching_cols)}")
        
        # Check semantic similarity if available
        if self.model and table_emb.embedding is not None:
            query_embedding = self.model.encode(query)
            similarity = self._cosine_similarity(query_embedding, table_emb.embedding)
            reasons.append(f"Semantic similarity: {similarity:.2%}")
        
        # Check relationships
        if table_emb.foreign_keys:
            related_tables = [fk['referred_table'] for fk in table_emb.foreign_keys]
            if any(word in ' '.join(related_tables).lower() for word in query_lower.split()):
                reasons.append(f"Related to: {', '.join(related_tables)}")
        
        if not reasons:
            reasons.append("Low relevance based on current analysis")
        
        return f"Table '{table_name}' relevance: " + "; ".join(reasons)
    
    def _save_embeddings_to_cache(self, cache_file: Path):
        """Save embeddings to cache file."""
        cache_data = {}
        for table_name, table_emb in self.table_embeddings.items():
            cache_data[table_name] = {
                'description': table_emb.description,
                'columns': table_emb.columns,
                'column_types': table_emb.column_types,
                'foreign_keys': table_emb.foreign_keys,
                'indexes': table_emb.indexes,
                'embedding': table_emb.embedding.tolist() if table_emb.embedding is not None else None
            }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def _load_embeddings_from_cache(self, cache_file: Path):
        """Load embeddings from cache file."""
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        for table_name, data in cache_data.items():
            embedding = None
            if data['embedding']:
                embedding = np.array(data['embedding'])
            
            self.table_embeddings[table_name] = TableEmbedding(
                table_name=table_name,
                description=data['description'],
                columns=data['columns'],
                column_types=data['column_types'],
                foreign_keys=data['foreign_keys'],
                indexes=data['indexes'],
                embedding=embedding
            )