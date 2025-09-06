"""
Domain-agnostic SQLAlchemy database toolkit.
Works automatically with any database schema through reflection.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text

from ..database.engine import get_engine, get_metadata
from ..config import config

logger = logging.getLogger(__name__)


class GenericDatabaseToolkit:
    """Database toolkit using SQLAlchemy reflection."""
    
    def __init__(self):
        """Initialize generic database toolkit."""
        self._engine = None
        self._initialized = False
    
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
        """Execute SQL query."""
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                
                if result.returns_rows:
                    rows = result.fetchall()
                    results = [dict(row._mapping) for row in rows]
                    row_count = len(results)
                else:
                    results = []
                    row_count = result.rowcount
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Apply row limit
                max_rows = config.safety.max_result_rows
                truncated = len(results) > max_rows
                if truncated:
                    results = results[:max_rows]
                
                return {
                    "success": True,
                    "data": results,
                    "execution_time_ms": execution_time_ms,
                    "row_count": row_count,
                    "truncated": truncated,
                    "error": None
                }
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Query execution failed: {e}")
            
            return {
                "success": False,
                "data": None,
                "execution_time_ms": execution_time_ms,
                "row_count": 0,
                "truncated": False,
                "error": str(e)
            }
    
    def get_table_names(self) -> List[str]:
        """Get all table names from the database."""
        metadata = get_metadata()
        return list(metadata.tables.keys())
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table information including columns, row count, and sample data."""
        metadata = get_metadata()
        if table_name not in metadata.tables:
            return {"error": f"Table '{table_name}' not found"}
        
        table = metadata.tables[table_name]
        
        # Get column information
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
        
        return {
            "table_name": table_name,
            "columns": columns,
            "row_count": self._get_row_count(table_name),
            "sample_data": self.get_sample_data(table_name, limit=3)
        }
    
    def _get_row_count(self, table_name: str) -> Optional[int]:
        """Get row count for table."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {e}")
            return None
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample data from table."""
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
            return [dict(row._mapping) for row in result]
    
    def get_table_relationships(self) -> Dict[str, List[str]]:
        """Get table relationships via foreign keys."""
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
      

# Global instance
db_toolkit = GenericDatabaseToolkit()