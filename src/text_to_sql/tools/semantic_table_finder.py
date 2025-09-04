"""
Semantic table finder using sentence-transformers.
Finds relevant tables using semantic similarity instead of keyword matching.
"""
import logging
import pickle
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .database_toolkit import db_toolkit

logger = logging.getLogger(__name__)


class SemanticTableFinder:
    """
    Find semantically relevant tables using sentence embeddings.
    """
    
    def __init__(self, engine, model_name: str = "all-mpnet-base-v2", cache_dir: str = ".embeddings_cache"):
        """Initialize with sentence transformer model."""
        # Note: engine parameter kept for compatibility but not used
        self.model = SentenceTransformer(model_name)
        self.cache_file = Path(cache_dir) / "table_embeddings.pkl"
        self.table_embeddings: Dict[str, np.ndarray] = {}
        self.table_descriptions: Dict[str, str] = {}
        
        # Load cached embeddings if available
        self._load_cache()
        
        logger.info(f"SemanticTableFinder initialized with model: {model_name}")
    
    def build_embeddings(self) -> None:
        """Build embeddings for all database tables."""
        logger.info("Building table embeddings...")
        
        for table_name in db_toolkit.get_table_names():
            description = self._create_table_description(table_name)
            embedding = self.model.encode([description])[0]
            
            self.table_descriptions[table_name] = description
            self.table_embeddings[table_name] = embedding
            
        logger.info(f"Built embeddings for {len(self.table_embeddings)} tables")
        
        # Save to cache
        self._save_cache()
    
    def find_relevant_tables(self, query: str, max_tables: int, threshold: float) -> List[Tuple[str, float, str]]:
        """
        Find tables relevant to query using semantic similarity.
        
        Returns: List of (table_name, similarity_score, description)
        """
        if not self.table_embeddings:
            self.build_embeddings()
        
        # Get query embedding
        query_embedding = self.model.encode([query])
        
        # Calculate similarities with all table embeddings
        table_names = list(self.table_embeddings.keys())
        table_embeds = np.array(list(self.table_embeddings.values()))
        
        similarities = cosine_similarity(query_embedding, table_embeds)[0]
        
        # Filter and sort results
        results = []
        for i, similarity in enumerate(similarities):
            if similarity >= threshold:
                table_name = table_names[i]
                description = self.table_descriptions[table_name]
                results.append((table_name, float(similarity), description))
        
        # Sort by similarity (descending) and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_tables]
    
    def _create_table_description(self, table_name: str) -> str:
        """Create text description of table for embedding - focus on semantic meaning."""
        table_info = db_toolkit.get_table_info(table_name)
        
        parts = [f"Table: {table_name}"]
        
        # Add column names only (no types or constraints)
        if table_info.get('columns'):
            column_names = [col['name'] for col in table_info['columns']]
            parts.append(f"Columns: {', '.join(column_names)}")
        
        # Add sample data for semantic context
        sample_data = db_toolkit.get_sample_data(table_name, limit=3)
        if sample_data:
            sample_parts = []
            for row in sample_data:
                # Include actual values for semantic understanding
                row_text = ", ".join([f"{k}: {v}" for k, v in row.items() if v is not None])
                sample_parts.append(row_text)
            parts.append(f"Sample data: {'; '.join(sample_parts)}")
        
        return ". ".join(parts)
    
    def _load_cache(self) -> None:
        """Load cached embeddings if available."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.table_embeddings = cache_data.get('embeddings', {})
                    self.table_descriptions = cache_data.get('descriptions', {})
                    logger.info(f"Loaded {len(self.table_embeddings)} cached embeddings")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
    
    def _save_cache(self) -> None:
        """Save embeddings to cache."""
        try:
            self.cache_file.parent.mkdir(exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                cache_data = {
                    'embeddings': self.table_embeddings,
                    'descriptions': self.table_descriptions
                }
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")