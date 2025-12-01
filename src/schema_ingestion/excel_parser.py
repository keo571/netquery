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
        self.suggested_queries: List[str] = []

        if not self.excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")

        self._parse_excel()
        logger.info(f"Parsed schema for {len(self.tables)} tables with {len(self.relationships)} relationships and {len(self.suggested_queries)} suggested queries")

    def _parse_excel(self):
        """Parse table_schema, mapping, and optional suggested_queries tabs from Excel file."""
        try:
            # Read required sheets
            table_schema_df = pd.read_excel(self.excel_file_path, sheet_name='table_schema')
            mapping_df = pd.read_excel(self.excel_file_path, sheet_name='mapping')

            # Parse table schema
            self._parse_table_schema(table_schema_df)

            # Parse relationships
            self._parse_relationships(mapping_df)

            # Parse suggested queries (REQUIRED sheet)
            suggested_queries_df = pd.read_excel(self.excel_file_path, sheet_name='suggested_queries')
            self._parse_suggested_queries(suggested_queries_df)

        except Exception as e:
            logger.error(f"Failed to parse Excel file: {e}")
            raise

    def _parse_table_schema(self, df: pd.DataFrame):
        """
        Parse table_schema tab with REQUIRED description columns.

        Required columns: table_name, column_name, data_type, is_nullable, table_description, column_description
        Optional columns: sample_values (comma-separated list of representative values)
        """
        # Validate required columns
        required_cols = ['table_name', 'column_name', 'data_type', 'is_nullable', 'table_description', 'column_description']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in Excel schema: {', '.join(missing_cols)}")

        # Check for optional sample_values column
        has_sample_values = 'sample_values' in df.columns

        for _, row in df.iterrows():
            table_name = str(row['table_name']).strip()
            column_name = str(row['column_name']).strip()
            data_type = str(row['data_type']).strip()
            is_nullable = str(row['is_nullable']).strip().upper()
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

            # Parse sample_values if present (comma-separated list)
            sample_values = None
            if has_sample_values and pd.notna(row['sample_values']):
                sample_values_str = str(row['sample_values']).strip()
                if sample_values_str and sample_values_str.lower() not in ('nan', 'none', ''):
                    # Split by comma and strip whitespace
                    sample_values = [v.strip() for v in sample_values_str.split(',') if v.strip()]
                    if not sample_values:  # Empty after filtering
                        sample_values = None

            # Add column info
            column_info = {
                'name': column_name,
                'type': data_type.lower(),
                'nullable': is_nullable in ('YES', 'Y', 'TRUE', '1'),
                'description': column_desc,
                'sample_values': sample_values
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

    def _parse_suggested_queries(self, df: pd.DataFrame):
        """
        Parse suggested_queries tab (REQUIRED).

        Expected format:
        - Column 'query': Natural language query suggestions (one per row)

        Example:
        | query |
        |-------|
        | Show all active load balancers |
        | Which SSL certificates expire in the next 30 days? |
        """
        if 'query' not in df.columns:
            raise ValueError("suggested_queries sheet missing required 'query' column")

        for _, row in df.iterrows():
            if pd.notna(row['query']):
                query = str(row['query']).strip()
                if query:  # Non-empty
                    self.suggested_queries.append(query)

        if not self.suggested_queries:
            raise ValueError("suggested_queries sheet is empty - at least one query is required")


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

    def get_suggested_queries(self) -> List[str]:
        """Get all suggested queries from the schema."""
        return self.suggested_queries


def create_schema_from_excel(excel_path: str) -> ExcelSchemaParser:
    """Factory function to create schema parser from Excel file."""
    return ExcelSchemaParser(excel_path)