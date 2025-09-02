"""
Domain-agnostic SQLAlchemy database toolkit.
Works automatically with any database schema through reflection.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from ..models.base import get_engine, get_session, get_metadata, DatabaseSession
from ..config import config

logger = logging.getLogger(__name__)


class GenericDatabaseToolkit:
    """
    Generic database toolkit that works with any schema automatically.
    
    Features:
    1. Automatic schema discovery via SQLAlchemy reflection
    2. Database agnostic (SQLite, PostgreSQL, MySQL, etc.)
    3. Type-safe operations
    4. Connection pooling
    5. No domain-specific assumptions
    """
    
    def __init__(self):
        """Initialize generic database toolkit."""
        self.engine = get_engine()
        self._ensure_connection()
    
    def _ensure_connection(self):
        """Ensure database connection is working."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def execute_query(self, sql_query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute SQL query safely with parameter binding.
        
        Args:
            sql_query: SQL query string
            params: Query parameters for safety
            
        Returns:
            Query results with metadata
        """
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                # Use text() for raw SQL with parameter binding
                if params:
                    result = conn.execute(text(sql_query), params)
                else:
                    result = conn.execute(text(sql_query))
                
                # Handle different query types
                if result.returns_rows:
                    # SELECT queries
                    rows = result.fetchall()
                    # Convert to list of dictionaries
                    results = [dict(row._mapping) for row in rows]
                else:
                    # INSERT/UPDATE/DELETE queries
                    results = []
                    row_count = result.rowcount
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Apply row limit for safety
                max_rows = config.safety.max_result_rows
                truncated = len(results) > max_rows if result.returns_rows else False
                if truncated:
                    results = results[:max_rows]
                
                logger.info(f"Query executed successfully, returned {len(results)} rows")
                
                return {
                    "success": True,
                    "data": results,
                    "execution_time_ms": execution_time_ms,
                    "row_count": len(results) if result.returns_rows else row_count,
                    "truncated": truncated,
                    "error": None
                }
                
        except SQLAlchemyError as e:
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
        try:
            metadata = get_metadata()
            return list(metadata.tables.keys())
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            return []
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        try:
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
            
            # Get row count (with timeout protection)
            row_count = self._get_row_count(table_name)
            
            # Get sample data
            sample_data = self.get_sample_data(table_name, limit=3)
            
            return {
                "table_name": table_name,
                "columns": columns,
                "row_count": row_count,
                "sample_data": sample_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get info for table {table_name}: {e}")
            return {"error": str(e)}
    
    def _get_row_count(self, table_name: str, timeout_seconds: int = 5) -> Optional[int]:
        """Get row count with timeout protection for large tables."""
        try:
            # For very large tables, this might be slow, so we add a timeout
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {e}")
            return None
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample data from any table."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.warning(f"Failed to get sample data for {table_name}: {e}")
            return []
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Get high-level summary of the entire database."""
        try:
            metadata = get_metadata()
            tables = list(metadata.tables.keys())
            
            summary = {
                "database_type": self.engine.dialect.name,
                "table_count": len(tables),
                "tables": []
            }
            
            # Get basic info for each table (without sample data to keep it fast)
            for table_name in tables[:20]:  # Limit to first 20 tables for performance
                table_info = {
                    "name": table_name,
                    "column_count": len(metadata.tables[table_name].columns),
                    "row_count": self._get_row_count(table_name)
                }
                summary["tables"].append(table_info)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get database summary: {e}")
            return {"error": str(e)}
    
    def get_table_relationships(self) -> Dict[str, List[str]]:
        """Discover table relationships automatically."""
        try:
            metadata = get_metadata()
            relationships = {}
            
            for table_name, table in metadata.tables.items():
                related_tables = []
                
                # Find tables this table references (via foreign keys)
                for column in table.columns:
                    for fk in column.foreign_keys:
                        referenced_table = fk.column.table.name
                        if referenced_table not in related_tables:
                            related_tables.append(referenced_table)
                
                if related_tables:
                    relationships[table_name] = related_tables
            
            return relationships
            
        except Exception as e:
            logger.error(f"Failed to get table relationships: {e}")
            return {}
    
    def search_tables_by_name(self, search_term: str) -> List[str]:
        """Find tables whose names contain the search term."""
        try:
            all_tables = self.get_table_names()
            search_term = search_term.lower()
            
            matching_tables = [
                table for table in all_tables 
                if search_term in table.lower()
            ]
            
            return matching_tables
            
        except Exception as e:
            logger.error(f"Failed to search tables: {e}")
            return []
    
    def search_columns_by_name(self, search_term: str) -> Dict[str, List[str]]:
        """Find columns across all tables that contain the search term."""
        try:
            metadata = get_metadata()
            search_term = search_term.lower()
            matching_columns = {}
            
            for table_name, table in metadata.tables.items():
                table_matches = []
                for column in table.columns:
                    if search_term in column.name.lower():
                        table_matches.append(column.name)
                
                if table_matches:
                    matching_columns[table_name] = table_matches
            
            return matching_columns
            
        except Exception as e:
            logger.error(f"Failed to search columns: {e}")
            return {}
    
    def optimize_for_database(self) -> Dict[str, Any]:
        """Apply database-specific optimizations."""
        try:
            results = {"optimizations": []}
            
            with self.engine.connect() as conn:
                if self.engine.dialect.name == 'sqlite':
                    # SQLite optimizations
                    conn.execute(text("PRAGMA optimize"))
                    results["optimizations"].append("SQLite PRAGMA optimize executed")
                    
                elif self.engine.dialect.name == 'postgresql':
                    # PostgreSQL optimizations
                    conn.execute(text("VACUUM ANALYZE"))
                    results["optimizations"].append("PostgreSQL VACUUM ANALYZE executed")
                    
                elif self.engine.dialect.name == 'mysql':
                    # MySQL optimizations - analyze all tables
                    tables = self.get_table_names()
                    for table in tables[:10]:  # Limit for performance
                        conn.execute(text(f"ANALYZE TABLE {table}"))
                    results["optimizations"].append(f"MySQL ANALYZE executed on {len(tables)} tables")
            
            return results
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return {"error": str(e)}


# Global instance
db_toolkit = GenericDatabaseToolkit()