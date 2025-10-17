"""
Canonical schema format for Netquery.

This module defines the canonical schema representation used across the system.
All schema sources (database introspection, Excel) are converted to this format.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal
from datetime import datetime
import json
from pathlib import Path


@dataclass
class ColumnSchema:
    """Schema for a single column."""
    name: str
    data_type: str
    description: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_nullable: bool = True
    default_value: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ColumnSchema':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class RelationshipSchema:
    """Schema for a table relationship (foreign key)."""
    foreign_key_column: str
    referenced_table: str
    referenced_column: str
    relationship_type: Literal['one_to_one', 'one_to_many', 'many_to_many'] = 'one_to_many'

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RelationshipSchema':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TableSchema:
    """Schema for a single table."""
    name: str
    description: str
    columns: Dict[str, ColumnSchema] = field(default_factory=dict)
    relationships: List[RelationshipSchema] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)

    # Metadata
    num_columns: int = 0
    num_fk_columns: int = 0

    def add_column(self, column: ColumnSchema):
        """Add a column to the table."""
        self.columns[column.name] = column
        self.num_columns = len(self.columns)
        if column.is_foreign_key:
            self.num_fk_columns = sum(1 for c in self.columns.values() if c.is_foreign_key)
        if column.is_primary_key:
            if column.name not in self.primary_keys:
                self.primary_keys.append(column.name)

    def add_relationship(self, relationship: RelationshipSchema):
        """Add a relationship to the table."""
        self.relationships.append(relationship)
        # Mark the FK column
        if relationship.foreign_key_column in self.columns:
            self.columns[relationship.foreign_key_column].is_foreign_key = True
            self.num_fk_columns = sum(1 for c in self.columns.values() if c.is_foreign_key)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'columns': {name: col.to_dict() for name, col in self.columns.items()},
            'relationships': [rel.to_dict() for rel in self.relationships],
            'primary_keys': self.primary_keys,
            'metadata': {
                'num_columns': self.num_columns,
                'num_fk_columns': self.num_fk_columns
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TableSchema':
        """Create from dictionary."""
        columns = {
            name: ColumnSchema.from_dict(col_data)
            for name, col_data in data.get('columns', {}).items()
        }
        relationships = [
            RelationshipSchema.from_dict(rel_data)
            for rel_data in data.get('relationships', [])
        ]
        metadata = data.get('metadata', {})

        return cls(
            name=data['name'],
            description=data['description'],
            columns=columns,
            relationships=relationships,
            primary_keys=data.get('primary_keys', []),
            num_columns=metadata.get('num_columns', len(columns)),
            num_fk_columns=metadata.get('num_fk_columns', 0)
        )


@dataclass
class CanonicalSchema:
    """
    Canonical schema representation for the entire database.

    This is the single source of truth for schema metadata across the system.
    All schema sources (database, Excel) are converted to this format.
    """
    # Unique identifier for this schema (for namespace isolation)
    schema_id: str = "default"  # e.g., "app_a_prod", "app_b_dev"

    version: str = "1.0.0"
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_type: Literal['database', 'excel', 'hybrid'] = 'database'
    source_location: str = ""
    database_type: str = "sqlite"  # sqlite, postgresql, mysql, etc.

    tables: Dict[str, TableSchema] = field(default_factory=dict)

    # Statistics
    total_tables: int = 0
    core_tables: int = 0
    detail_tables: int = 0
    junction_tables: int = 0
    system_tables: int = 0

    def add_table(self, table: TableSchema):
        """Add a table to the schema."""
        self.tables[table.name] = table
        self._update_statistics()

    def _update_statistics(self):
        """Update schema statistics."""
        self.total_tables = len(self.tables)

    def get_table(self, table_name: str) -> Optional[TableSchema]:
        """Get a table by name."""
        return self.tables.get(table_name)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'schema_id': self.schema_id,
            'version': self.version,
            'generated_at': self.generated_at,
            'source': {
                'type': self.source_type,
                'location': self.source_location,
                'database_type': self.database_type
            },
            'statistics': {
                'total_tables': self.total_tables,
                'core_tables': self.core_tables,
                'detail_tables': self.detail_tables,
                'junction_tables': self.junction_tables,
                'system_tables': self.system_tables
            },
            'tables': {name: table.to_dict() for name, table in self.tables.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CanonicalSchema':
        """Create from dictionary (for loading from JSON)."""
        source = data.get('source', {})
        statistics = data.get('statistics', {})
        tables = {
            name: TableSchema.from_dict(table_data)
            for name, table_data in data.get('tables', {}).items()
        }

        schema = cls(
            schema_id=data.get('schema_id', 'default'),
            version=data.get('version', '1.0.0'),
            generated_at=data.get('generated_at', datetime.utcnow().isoformat()),
            source_type=source.get('type', 'database'),
            source_location=source.get('location', ''),
            database_type=source.get('database_type', 'sqlite'),
            tables=tables,
            total_tables=statistics.get('total_tables', len(tables)),
            core_tables=statistics.get('core_tables', 0),
            detail_tables=statistics.get('detail_tables', 0),
            junction_tables=statistics.get('junction_tables', 0),
            system_tables=statistics.get('system_tables', 0)
        )
        schema._update_statistics()
        return schema

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> 'CanonicalSchema':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save(self, file_path: str):
        """Save schema to JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())

    @classmethod
    def load(cls, file_path: str) -> 'CanonicalSchema':
        """Load schema from JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")
        json_str = path.read_text()
        return cls.from_json(json_str)

    def validate(self) -> List[str]:
        """
        Validate the schema for consistency.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for table_name, table in self.tables.items():
            # Check table name consistency
            if table.name != table_name:
                errors.append(f"Table key '{table_name}' doesn't match table name '{table.name}'")

            # Check relationships reference valid tables
            for rel in table.relationships:
                if rel.referenced_table not in self.tables:
                    errors.append(
                        f"Table '{table_name}' references non-existent table '{rel.referenced_table}'"
                    )

                # Check FK column exists
                if rel.foreign_key_column not in table.columns:
                    errors.append(
                        f"Table '{table_name}' relationship references non-existent column "
                        f"'{rel.foreign_key_column}'"
                    )

            # Check primary keys exist
            for pk in table.primary_keys:
                if pk not in table.columns:
                    errors.append(
                        f"Table '{table_name}' has primary key '{pk}' that doesn't exist in columns"
                    )

        return errors

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Schema ID: {self.schema_id}",
            f"Schema Version: {self.version}",
            f"Generated: {self.generated_at}",
            f"Source: {self.source_type} ({self.source_location})",
            f"Database: {self.database_type}",
            f"Tables: {self.total_tables}",
        ]
        return "\n".join(lines)

    def get_embedding_namespace(self) -> str:
        """
        Get unique namespace for embedding isolation.

        This ensures embeddings are isolated per schema_id,
        preventing cross-contamination between different applications/environments.

        Returns:
            Namespace string (e.g., "app_a_prod", "app_b_dev")
        """
        return self.schema_id
