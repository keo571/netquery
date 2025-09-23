"""
Enhanced database toolkit with Excel schema support.
Combines database connectivity with Excel-defined schema metadata.
"""
import logging
from typing import Dict, List, Any, Optional
from .database_toolkit import DatabaseToolkit
from .excel_schema_parser import ExcelSchemaParser

logger = logging.getLogger(__name__)


class ExcelDatabaseToolkit(DatabaseToolkit):
    """
    Database toolkit enhanced with Excel schema definitions.
    Falls back to Excel schema when database introspection fails.
    """

    def __init__(self, engine, excel_schema_path: Optional[str] = None):
        """Initialize with database engine and optional Excel schema."""
        super().__init__(engine)
        self.excel_schema: Optional[ExcelSchemaParser] = None

        if excel_schema_path:
            try:
                self.excel_schema = ExcelSchemaParser(excel_schema_path)
                logger.info(f"Loaded Excel schema from {excel_schema_path}")
            except Exception as e:
                logger.warning(f"Failed to load Excel schema: {e}")

    def get_table_names(self) -> List[str]:
        """Get table names from Excel schema if available, fallback to database."""
        if self.excel_schema:
            return self.excel_schema.get_table_names()
        return super().get_table_names()

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table info from Excel schema if available, fallback to database."""
        if self.excel_schema:
            excel_info = self.excel_schema.get_table_info(table_name)
            if excel_info:
                return excel_info

        # Fallback to database introspection
        try:
            return super().get_table_info(table_name)
        except Exception as e:
            logger.warning(f"Failed to get table info from database for {table_name}: {e}")
            # Return minimal info if both Excel and database fail
            return {
                'name': table_name,
                'columns': [{'name': 'id', 'type': 'integer'}],
                'description': f'Table: {table_name}'
            }

    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample data from database (Excel doesn't contain data)."""
        try:
            return super().get_sample_data(table_name, limit)
        except Exception as e:
            logger.warning(f"Failed to get sample data for {table_name}: {e}")
            return []

    def get_relationships(self) -> List[Dict]:
        """Get relationships from Excel schema if available."""
        if self.excel_schema:
            return self.excel_schema.get_relationships()
        return []

    def get_related_tables(self, table_name: str) -> List[str]:
        """Get tables related to the given table."""
        if self.excel_schema:
            return self.excel_schema.get_related_tables(table_name)
        return []

    def validate_table_exists(self, table_name: str) -> bool:
        """Check if table exists in schema or database."""
        if self.excel_schema:
            return table_name in self.excel_schema.get_table_names()
        return super().validate_table_exists(table_name)

    def get_schema_summary(self) -> Dict[str, Any]:
        """Get comprehensive schema summary."""
        tables = self.get_table_names()
        relationships = self.get_relationships()

        return {
            'total_tables': len(tables),
            'tables': tables,
            'total_relationships': len(relationships),
            'relationships': relationships,
            'schema_source': 'excel' if self.excel_schema else 'database'
        }


# Global instance - will be initialized when engine is available
excel_db_toolkit: Optional[ExcelDatabaseToolkit] = None


def init_excel_toolkit(engine, excel_path: Optional[str] = None):
    """Initialize the global Excel database toolkit."""
    global excel_db_toolkit
    excel_db_toolkit = ExcelDatabaseToolkit(engine, excel_path)
    return excel_db_toolkit


def get_excel_toolkit() -> ExcelDatabaseToolkit:
    """Get the global Excel database toolkit instance."""
    if excel_db_toolkit is None:
        raise RuntimeError("Excel toolkit not initialized. Call init_excel_toolkit first.")
    return excel_db_toolkit