"""
Database toolkit for Text-to-SQL agent.
"""
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import time

from ..config import config

logger = logging.getLogger(__name__)


class DatabaseToolkit:
    """Database operations toolkit."""
    
    def __init__(self):
        self.db_path = None
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists."""
        # Extract path from database URL
        if config.database.database_url.startswith("sqlite:///"):
            self.db_path = config.database.database_url.replace("sqlite:///", "")
        else:
            # Default path
            self.db_path = str(Path(__file__).parent.parent / "infrastructure.db")
        
        # Create database if it doesn't exist
        if not Path(self.db_path).exists():
            logger.info(f"Database not found at {self.db_path}, creating...")
            from ..create_sample_data import create_infrastructure_database
            self.db_path = create_infrastructure_database(self.db_path)
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """Execute SQL query and return results."""
        start_time = time.time()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                cursor = conn.cursor()
                cursor.execute(sql_query)
                
                # Fetch results
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                results = [dict(row) for row in rows]
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                logger.info(f"Query executed successfully, returned {len(results)} rows")
                
                # Apply row limit for safety
                max_rows = config.safety.max_result_rows
                truncated = len(results) > max_rows
                if truncated:
                    results = results[:max_rows]
                
                return {
                    "success": True,
                    "data": results,
                    "execution_time_ms": execution_time_ms,
                    "row_count": len(results),
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
        """Get all table names."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            return []
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get column info - convert tuples to dictionaries
                cursor.execute(f"PRAGMA table_info({table_name})")
                column_rows = cursor.fetchall()
                
                # Convert column tuples to dictionaries
                columns = []
                for row in column_rows:
                    columns.append({
                        'cid': row[0],
                        'name': row[1], 
                        'type': row[2],
                        'notnull': row[3],
                        'dflt_value': row[4],
                        'pk': row[5]
                    })
                
                # Get foreign keys - convert tuples to dictionaries  
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fk_rows = cursor.fetchall()
                
                foreign_keys = []
                for row in fk_rows:
                    foreign_keys.append({
                        'id': row[0],
                        'seq': row[1],
                        'table': row[2],
                        'from': row[3],
                        'to': row[4],
                        'on_update': row[5],
                        'on_delete': row[6],
                        'match': row[7]
                    })
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                return {
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                    "row_count": row_count
                }
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {}
    
    def get_sample_data(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get sample data from table."""
        try:
            return self.execute_query(f"SELECT * FROM {table_name} LIMIT {limit}")
        except Exception as e:
            logger.error(f"Failed to get sample data from {table_name}: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            table_names = self.get_table_names()
            total_rows = 0
            table_stats = {}
            
            for table_name in table_names:
                info = self.get_table_info(table_name)
                row_count = info.get("row_count", 0)
                total_rows += row_count
                table_stats[table_name] = {
                    "rows": row_count,
                    "columns": len(info.get("columns", []))
                }
            
            return {
                "total_tables": len(table_names),
                "total_rows": total_rows,
                "table_stats": table_stats,
                "database_path": self.db_path
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global instance
db_toolkit = DatabaseToolkit()
