"""
Schema builder - converts database/Excel sources to canonical format.
"""
import logging
from typing import Optional, Dict, Set
from sqlalchemy.engine import Engine
from sqlalchemy import inspect

from src.schema_ingestion.canonical import (
    CanonicalSchema, TableSchema, ColumnSchema, RelationshipSchema
)
from src.schema_ingestion.excel_parser import ExcelSchemaParser

logger = logging.getLogger(__name__)

# System table prefixes to skip
SYSTEM_PREFIXES = (
    'sqlite_',  # SQLite system tables
    'pg_',      # PostgreSQL catalog
    'information_schema',  # SQL standard
    'mysql',    # MySQL system
    'sys_',     # Generic system
)


class SchemaBuilder:
    """Build canonical schema from database or Excel sources."""

    def __init__(self):
        """Initialize schema builder."""
        self.canonical_schema: Optional[CanonicalSchema] = None

    def build_from_database(
        self,
        engine: Engine,
        database_url: str,
        schema_id: str = "default",
        include_system_tables: bool = False
    ) -> CanonicalSchema:
        """
        Build canonical schema from database introspection.

        Args:
            engine: SQLAlchemy engine
            database_url: Database connection URL
            schema_id: Unique identifier for this schema (for namespace isolation)
            include_system_tables: Include system tables in schema

        Returns:
            CanonicalSchema object
        """
        logger.info(f"Building schema from database: {database_url}")
        logger.info(f"Schema ID: {schema_id}")

        # Determine database type from URL
        db_type = self._get_database_type(database_url)

        # Create canonical schema
        canonical = CanonicalSchema(
            schema_id=schema_id,
            source_type='database',
            source_location=database_url,
            database_type=db_type
        )

        # Introspect database
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        # Filter system tables if needed
        if not include_system_tables:
            table_names = [t for t in table_names if not self._is_system_table(t)]

        logger.info(f"Found {len(table_names)} tables")

        # Build tables
        for table_name in table_names:
            table_schema = self._build_table_from_database(
                inspector,
                table_name
            )
            canonical.add_table(table_schema)

        logger.info(f"Built schema with {canonical.total_tables} tables")
        self.canonical_schema = canonical
        return canonical

    def build_from_excel(
        self,
        excel_path: str,
        schema_id: str = "default",
        include_system_tables: bool = False
    ) -> CanonicalSchema:
        """
        Build canonical schema from Excel file.

        Args:
            excel_path: Path to Excel schema file
            schema_id: Unique identifier for this schema (for namespace isolation)
            include_system_tables: Include system tables in schema

        Returns:
            CanonicalSchema object
        """
        logger.info(f"Building schema from Excel: {excel_path}")
        logger.info(f"Schema ID: {schema_id}")

        # Parse Excel
        excel_parser = ExcelSchemaParser(excel_path)

        # Create canonical schema
        canonical = CanonicalSchema(
            schema_id=schema_id,
            source_type='excel',
            source_location=excel_path,
            database_type='unknown'  # Excel doesn't specify DB type
        )

        # Get all tables from Excel
        table_names = list(excel_parser.tables.keys())

        # Filter system tables if needed
        if not include_system_tables:
            table_names = [t for t in table_names if not self._is_system_table(t)]

        logger.info(f"Found {len(table_names)} tables in Excel")

        # Build tables
        for table_name in table_names:
            table_schema = self._build_table_from_excel(
                excel_parser,
                table_name
            )
            canonical.add_table(table_schema)

        logger.info(f"Built schema with {canonical.total_tables} tables")
        self.canonical_schema = canonical
        return canonical

    def _build_table_from_database(
        self,
        inspector,
        table_name: str
    ) -> TableSchema:
        """Build TableSchema from database introspection."""

        # Get columns
        db_columns = inspector.get_columns(table_name)

        # Get primary keys
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_keys = pk_constraint.get('constrained_columns', [])

        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name)

        # Create table schema - use table name as description
        table = TableSchema(
            name=table_name,
            description=f"Table: {table_name}"
        )

        # Add columns
        for col in db_columns:
            column_schema = ColumnSchema(
                name=col['name'],
                data_type=str(col['type']),
                description=f"Column: {col['name']}",
                is_primary_key=col['name'] in primary_keys,
                is_nullable=col.get('nullable', True),
                default_value=str(col.get('default')) if col.get('default') is not None else None
            )
            table.add_column(column_schema)

        # Add relationships
        for fk in fks:
            for i, constrained_col in enumerate(fk['constrained_columns']):
                relationship = RelationshipSchema(
                    foreign_key_column=constrained_col,
                    referenced_table=fk['referred_table'],
                    referenced_column=fk['referred_columns'][i] if i < len(fk['referred_columns']) else 'id'
                )
                table.add_relationship(relationship)

        return table

    def _build_table_from_excel(
        self,
        excel_parser: ExcelSchemaParser,
        table_name: str
    ) -> TableSchema:
        """Build TableSchema from Excel."""

        # Get table info from Excel
        table_info = excel_parser.get_table_info(table_name)
        if not table_info:
            raise ValueError(f"Table '{table_name}' not found in Excel schema")

        # Create table schema with Excel description
        table = TableSchema(
            name=table_name,
            description=table_info.get('description', f"Table: {table_name}")
        )

        # Add columns with Excel descriptions
        for col_info in table_info.get('columns', []):
            column_schema = ColumnSchema(
                name=col_info['name'],
                data_type=col_info.get('type', 'TEXT'),
                description=col_info.get('description', f"Column: {col_info['name']}"),
                is_primary_key=col_info.get('is_primary_key', col_info['name'] == 'id'),
                is_nullable=True  # Excel doesn't specify nullability
            )
            table.add_column(column_schema)

        # Add relationships from Excel mappings
        for mapping in excel_parser.get_relationships():
            if mapping['table_a'] == table_name:
                relationship = RelationshipSchema(
                    foreign_key_column=mapping['column_a'],
                    referenced_table=mapping['table_b'],
                    referenced_column=mapping['column_b']
                )
                table.add_relationship(relationship)
            elif mapping['table_b'] == table_name:
                relationship = RelationshipSchema(
                    foreign_key_column=mapping['column_b'],
                    referenced_table=mapping['table_a'],
                    referenced_column=mapping['column_a']
                )
                table.add_relationship(relationship)

        return table

    def _is_system_table(self, table_name: str) -> bool:
        """Check if a table is a system table."""
        return any(table_name.startswith(prefix) for prefix in SYSTEM_PREFIXES)

    def _get_database_type(self, database_url: str) -> str:
        """Extract database type from connection URL."""
        if 'sqlite' in database_url:
            return 'sqlite'
        elif 'postgresql' in database_url or 'postgres' in database_url:
            return 'postgresql'
        elif 'mysql' in database_url:
            return 'mysql'
        elif 'mssql' in database_url or 'sqlserver' in database_url:
            return 'sqlserver'
        else:
            return 'unknown'
