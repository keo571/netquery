"""
Excel Schema Parser for databases without introspectable schemas.
Reads table definitions and relationships from Excel files.
"""
import logging
import pandas as pd
from typing import Dict, List, Tuple, Optional
from pathlib import Path

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
        """Parse table_schema tab: table_name | column_name"""
        for _, row in df.iterrows():
            table_name = str(row['table_name']).strip()
            column_name = str(row['column_name']).strip()

            # Initialize table if not exists
            if table_name not in self.tables:
                self.tables[table_name] = {
                    'name': table_name,
                    'columns': [],
                    'description': self._generate_table_description(table_name)
                }

            # Add column info
            column_info = {
                'name': column_name,
                'type': self._infer_column_type(column_name),
                'description': self._generate_column_description(column_name)
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
        """Infer column type based on column name patterns."""
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

    def _generate_column_description(self, column_name: str) -> str:
        """Generate descriptive text for column based on name."""
        column_lower = column_name.lower()

        if column_lower == 'id':
            return 'Primary key identifier'
        elif column_lower.endswith('_id'):
            table_ref = column_lower.replace('_id', '')
            return f'Foreign key reference to {table_ref} table'
        elif 'name' in column_lower:
            return 'Name or title field'
        elif 'date' in column_lower or 'time' in column_lower:
            return 'Date/time field'
        elif 'status' in column_lower:
            return 'Status or state field'
        else:
            return f'{column_name} field'

    def _generate_table_description(self, table_name: str) -> str:
        """Generate semantic description for table based on name patterns."""
        table_lower = table_name.lower()

        # Common table patterns
        if 'user' in table_lower:
            return 'User account and profile information'
        elif 'order' in table_lower:
            return 'Order transactions and purchase records'
        elif 'product' in table_lower:
            return 'Product catalog and inventory data'
        elif 'customer' in table_lower:
            return 'Customer information and details'
        elif 'mapping' in table_lower or 'junction' in table_lower:
            return 'Junction table for many-to-many relationships'
        elif any(word in table_lower for word in ['log', 'audit', 'history']):
            return 'Historical records and audit trail'
        elif 'config' in table_lower or 'setting' in table_lower:
            return 'Configuration and system settings'
        else:
            return f'{table_name.replace("_", " ").title()} data table'

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

    def export_to_yaml(self, output_path: str):
        """Export parsed schema to YAML format for table descriptions."""
        import yaml

        descriptions = {}
        for table_name, table_info in self.tables.items():
            # Create rich description including columns and relationships
            desc_parts = [table_info['description']]

            # Add key columns
            key_columns = [col['name'] for col in table_info['columns']
                          if not col['name'].endswith('_id')]
            if key_columns:
                desc_parts.append(f"Key fields: {', '.join(key_columns)}")

            # Add relationship info
            related = self.get_related_tables(table_name)
            if related:
                desc_parts.append(f"Related to: {', '.join(related)}")

            descriptions[table_name] = '. '.join(desc_parts)

        with open(output_path, 'w') as f:
            yaml.dump(descriptions, f, default_flow_style=False)

        logger.info(f"Exported table descriptions to {output_path}")


def create_schema_from_excel(excel_path: str) -> ExcelSchemaParser:
    """Factory function to create schema parser from Excel file."""
    return ExcelSchemaParser(excel_path)