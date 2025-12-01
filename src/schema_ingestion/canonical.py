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
    """
    Schema for a single column.

    sample_values: Optional list of representative values for this column.
    Used in LLM prompts instead of querying the database for sample data.
    Particularly useful for enum-like columns (status, type, category).
    Example: ["active", "inactive", "maintenance"] for a status column.

    Note: Foreign keys are tracked via TableSchema.relationships array.
    """
    name: str
    data_type: str
    description: str
    is_nullable: bool = True
    sample_values: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding the redundant 'name' field."""
        d = asdict(self)
        d.pop('name', None)  # Remove name since it's the dict key
        return d

    @classmethod
    def from_dict(cls, name: str, data: Dict) -> 'ColumnSchema':
        """Create from dictionary, restoring the 'name' field."""
        return cls(name=name, **data)


@dataclass
class RelationshipSchema:
    """
    Schema for a table relationship.

    Describes how to JOIN this table to another table.
    Does NOT require actual FK constraints in the database.

    Example:
        Table: backend_mappings
        Relationship: foreign_key_column='load_balancer_id'
                     referenced_table='load_balancers'
                     referenced_column='id'

        JOIN: backend_mappings.load_balancer_id = load_balancers.id
    """
    foreign_key_column: str  # Column in this table (e.g., "load_balancer_id")
    referenced_table: str    # Table to join to (e.g., "load_balancers")
    referenced_column: str   # Column in referenced table (e.g., "id")

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

    def add_column(self, column: ColumnSchema):
        """Add a column to the table."""
        self.columns[column.name] = column

    def add_relationship(self, relationship: RelationshipSchema):
        """Add a relationship to the table."""
        self.relationships.append(relationship)

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding the redundant 'name' field."""
        return {
            # 'name' is excluded - it's already the dict key
            'description': self.description,
            'columns': {name: col.to_dict() for name, col in self.columns.items()},
            'relationships': [rel.to_dict() for rel in self.relationships]
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict) -> 'TableSchema':
        """Create from dictionary, restoring the 'name' field."""
        columns = {
            col_name: ColumnSchema.from_dict(col_name, col_data)
            for col_name, col_data in data.get('columns', {}).items()
        }
        relationships = [
            RelationshipSchema.from_dict(rel_data)
            for rel_data in data.get('relationships', [])
        ]

        return cls(
            name=name,  # Name comes from dict key
            description=data['description'],
            columns=columns,
            relationships=relationships
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

    # Optional custom suggested queries from schema source (e.g., Excel)
    suggested_queries: List[str] = field(default_factory=list)

    # Statistics
    total_tables: int = 0

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
        d = {
            'schema_id': self.schema_id,
            'version': self.version,
            'generated_at': self.generated_at,
            'source': {
                'type': self.source_type,
                'location': self.source_location,
                'database_type': self.database_type
            },
            'statistics': {
                'total_tables': self.total_tables
            },
            'tables': {name: table.to_dict() for name, table in self.tables.items()}
        }

        # Include suggested_queries if present
        if self.suggested_queries:
            d['suggested_queries'] = self.suggested_queries

        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'CanonicalSchema':
        """Create from dictionary (for loading from JSON)."""
        source = data.get('source', {})
        statistics = data.get('statistics', {})
        tables = {
            table_name: TableSchema.from_dict(table_name, table_data)
            for table_name, table_data in data.get('tables', {}).items()
        }

        schema = cls(
            schema_id=data.get('schema_id', 'default'),
            version=data.get('version', '1.0.0'),
            generated_at=data.get('generated_at', datetime.utcnow().isoformat()),
            source_type=source.get('type', 'database'),
            source_location=source.get('location', ''),
            database_type=source.get('database_type', 'sqlite'),
            tables=tables,
            suggested_queries=data.get('suggested_queries', []),
            total_tables=statistics.get('total_tables', len(tables))
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
