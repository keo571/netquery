"""
Excel Schema Parser for databases without introspectable schemas.
Reads table definitions and relationships from Excel files.
"""
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExcelSchemaParser:
    """Parse database schema from Excel file with table_schema and mapping tabs."""

    def __init__(self, excel_file_path: str):
        """Initialize with path to Excel file."""
        self.excel_file_path = Path(excel_file_path)
        self.tables: Dict[str, Dict] = {}
        self.relationships: List[Dict] = []

        if not self.excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")

        self._parse_excel()
        logger.info(f"Parsed schema for {len(self.tables)} tables with {len(self.relationships)} relationships")

    def _parse_excel(self):
        """Parse both table_schema and mapping tabs from Excel file."""
        try:
            # Read both sheets
            table_schema_df = pd.read_excel(self.excel_file_path, sheet_name='table_schema')
            mapping_df = pd.read_excel(self.excel_file_path, sheet_name='mapping')

            # Parse table schema
            self._parse_table_schema(table_schema_df)

            # Parse relationships
            self._parse_relationships(mapping_df)

        except Exception as e:
            logger.error(f"Failed to parse Excel file: {e}")
            raise

    def _parse_table_schema(self, df: pd.DataFrame):
        """
        Parse table_schema tab with REQUIRED description columns.

        Required columns: table_name, column_name, table_description, column_description
        """
        # Validate required columns
        required_cols = ['table_name', 'column_name', 'table_description', 'column_description']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in Excel schema: {', '.join(missing_cols)}")

        for _, row in df.iterrows():
            table_name = str(row['table_name']).strip()
            column_name = str(row['column_name']).strip()
            table_desc = str(row['table_description']).strip()
            column_desc = str(row['column_description']).strip()

            # Validate descriptions are not empty
            if not table_desc:
                raise ValueError(f"Empty table_description for table '{table_name}'. Descriptions are required.")
            if not column_desc:
                raise ValueError(f"Empty column_description for column '{table_name}.{column_name}'. Descriptions are required.")

            # Initialize table if not exists
            if table_name not in self.tables:
                self.tables[table_name] = {
                    'name': table_name,
                    'columns': [],
                    'description': table_desc
                }

            # Add column info
            column_info = {
                'name': column_name,
                'type': self._infer_column_type(column_name),
                'description': column_desc
            }
            self.tables[table_name]['columns'].append(column_info)

    def _parse_relationships(self, df: pd.DataFrame):
        """Parse mapping tab: table_a | column_a | table_b | column_b"""
        # Assuming columns are: table_a, column_a, table_b, column_b
        for _, row in df.iterrows():
            relationship = {
                'table_a': str(row.iloc[0]).strip(),
                'column_a': str(row.iloc[1]).strip(),
                'table_b': str(row.iloc[2]).strip(),
                'column_b': str(row.iloc[3]).strip(),
                'type': 'foreign_key'
            }
            self.relationships.append(relationship)

    def _infer_column_type(self, column_name: str) -> str:
        """Infer column type based on column name patterns (best effort)."""
        column_lower = column_name.lower()

        if column_lower == 'id' or column_lower.endswith('_id'):
            return 'integer'
        elif 'date' in column_lower or 'time' in column_lower:
            return 'timestamp'
        elif any(word in column_lower for word in ['amount', 'price', 'cost', 'value']):
            return 'decimal'
        elif any(word in column_lower for word in ['count', 'number', 'qty', 'quantity']):
            return 'integer'
        elif any(word in column_lower for word in ['rate', 'percentage', 'percent']):
            return 'decimal'
        else:
            return 'text'

    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """Get complete table information including columns."""
        return self.tables.get(table_name)

    def get_table_names(self) -> List[str]:
        """Get list of all table names."""
        return list(self.tables.keys())

    def get_relationships(self) -> List[Dict]:
        """Get all table relationships."""
        return self.relationships

    def get_related_tables(self, table_name: str) -> List[str]:
        """Get list of tables related to given table."""
        related = set()
        for rel in self.relationships:
            if rel['table_a'] == table_name:
                related.add(rel['table_b'])
            elif rel['table_b'] == table_name:
                related.add(rel['table_a'])
        return list(related)


def create_schema_from_excel(excel_path: str) -> ExcelSchemaParser:
    """Factory function to create schema parser from Excel file."""
    return ExcelSchemaParser(excel_path)