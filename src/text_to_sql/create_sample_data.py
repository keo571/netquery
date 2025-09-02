"""
Generic sample data creation utility.
Works with any database schema through SQLAlchemy reflection.
"""
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from .models.base import get_engine, get_metadata, DatabaseSession

logger = logging.getLogger(__name__)


class GenericSampleDataGenerator:
    """
    Generate realistic sample data for any database schema automatically.
    
    Uses SQLAlchemy reflection to understand the schema and generates
    appropriate data based on column names and types.
    """
    
    def __init__(self):
        """Initialize data generator."""
        self.engine = get_engine()
        self.metadata = get_metadata()
        
        # Generic data patterns for common column types
        self.sample_names = [
            "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown", 
            "Emma Davis", "Frank Wilson", "Grace Miller", "Henry Moore"
        ]
        
        self.sample_emails = [
            "alice@company.com", "bob@company.com", "carol@company.com",
            "david@company.com", "emma@company.com", "frank@company.com"
        ]
        
        self.sample_statuses = ["active", "inactive", "pending", "completed", "cancelled"]
        self.sample_types = ["standard", "premium", "basic", "advanced", "custom"]
        self.sample_categories = ["category_a", "category_b", "category_c", "other"]
        
    def create_sample_database(self, tables: Optional[List[str]] = None, 
                              records_per_table: int = 20) -> Dict[str, int]:
        """
        Create sample data for database tables.
        
        Args:
            tables: Specific tables to populate (None = all tables)
            records_per_table: Number of records to create per table
            
        Returns:
            Dictionary with table names and record counts created
        """
        logger.info("Generating sample data for database...")
        
        if not self.metadata.tables:
            logger.warning("No tables found in database")
            return {}
        
        # Determine which tables to populate
        target_tables = tables or list(self.metadata.tables.keys())
        results = {}
        
        with DatabaseSession() as session:
            # Create data in dependency order (tables without foreign keys first)
            ordered_tables = self._order_tables_by_dependencies(target_tables)
            
            for table_name in ordered_tables:
                if table_name in self.metadata.tables:
                    count = self._populate_table(session, table_name, records_per_table)
                    results[table_name] = count
                    logger.info(f"Created {count} records in {table_name}")
        
        logger.info(f"Sample data generation completed for {len(results)} tables")
        return results
    
    def _order_tables_by_dependencies(self, table_names: List[str]) -> List[str]:
        """Order tables by foreign key dependencies."""
        ordered = []
        remaining = set(table_names)
        
        while remaining:
            # Find tables with no dependencies in remaining set
            ready = []
            for table_name in remaining:
                table = self.metadata.tables[table_name]
                deps = {fk.column.table.name for fk in table.foreign_keys}
                # Ready if no dependencies or all dependencies already processed
                if not deps or deps.issubset(set(ordered)):
                    ready.append(table_name)
            
            if not ready:
                # Circular dependency or isolated tables
                ready = [next(iter(remaining))]
            
            ordered.extend(ready)
            remaining -= set(ready)
        
        return ordered
    
    def _populate_table(self, session, table_name: str, count: int) -> int:
        """Populate a single table with sample data."""
        table = self.metadata.tables[table_name]
        records_created = 0
        
        for i in range(count):
            try:
                record_data = self._generate_record_data(table, i)
                
                # Create raw SQL insert to avoid ORM complexity
                insert_stmt = table.insert().values(**record_data)
                session.execute(insert_stmt)
                records_created += 1
                
            except Exception as e:
                logger.warning(f"Failed to create record {i} for {table_name}: {e}")
                continue
        
        session.commit()
        return records_created
    
    def _generate_record_data(self, table, index: int) -> Dict[str, Any]:
        """Generate realistic data for a single record."""
        data = {}
        
        for column in table.columns:
            # Skip auto-increment primary keys
            if column.primary_key and column.autoincrement:
                continue
            
            # Handle foreign keys
            if column.foreign_keys:
                fk = next(iter(column.foreign_keys))
                ref_table = fk.column.table
                data[column.name] = self._get_random_fk_value(ref_table, fk.column)
                continue
            
            # Generate value based on column name and type
            value = self._generate_column_value(column, index)
            if value is not None:
                data[column.name] = value
        
        return data
    
    def _get_random_fk_value(self, ref_table, ref_column):
        """Get a random value from referenced table."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    f"SELECT {ref_column.name} FROM {ref_table.name} ORDER BY RANDOM() LIMIT 1"
                )
                row = result.fetchone()
                return row[0] if row else 1
        except:
            return 1  # Fallback
    
    def _generate_column_value(self, column, index: int) -> Any:
        """Generate appropriate value based on column name and type."""
        col_name = column.name.lower()
        col_type = str(column.type).lower()
        
        # Handle specific column name patterns
        if any(pattern in col_name for pattern in ['name', 'title']):
            if 'first' in col_name:
                return random.choice(['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa'])
            elif 'last' in col_name:
                return random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])
            else:
                return f"{col_name.title()} {index + 1}"
        
        elif 'email' in col_name:
            return random.choice(self.sample_emails)
        
        elif any(pattern in col_name for pattern in ['status', 'state']):
            return random.choice(self.sample_statuses)
        
        elif 'type' in col_name:
            return random.choice(self.sample_types)
        
        elif 'category' in col_name:
            return random.choice(self.sample_categories)
        
        elif any(pattern in col_name for pattern in ['description', 'notes', 'comment']):
            return f"Sample {col_name} for record {index + 1}"
        
        elif any(pattern in col_name for pattern in ['created', 'updated', 'modified']) and 'date' in col_name:
            return datetime.utcnow() - timedelta(days=random.randint(0, 365))
        
        elif 'date' in col_name or 'time' in col_name:
            return datetime.utcnow() - timedelta(days=random.randint(0, 30))
        
        elif any(pattern in col_name for pattern in ['url', 'link', 'website']):
            return f"https://example-{index + 1}.com"
        
        elif 'phone' in col_name:
            return f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        
        elif any(pattern in col_name for pattern in ['address', 'street']):
            return f"{random.randint(1, 999)} Sample Street"
        
        elif 'city' in col_name:
            return random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'])
        
        elif any(pattern in col_name for pattern in ['country', 'nation']):
            return random.choice(['USA', 'Canada', 'UK', 'Germany', 'France'])
        
        elif any(pattern in col_name for pattern in ['code', 'key', 'token']):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Handle by SQL type
        elif any(t in col_type for t in ['int', 'integer', 'number']):
            if 'id' in col_name:
                return index + 1
            elif any(pattern in col_name for pattern in ['count', 'quantity', 'amount']):
                return random.randint(1, 100)
            elif any(pattern in col_name for pattern in ['price', 'cost', 'balance']):
                return round(random.uniform(10.0, 1000.0), 2)
            else:
                return random.randint(1, 1000)
        
        elif any(t in col_type for t in ['decimal', 'numeric', 'float', 'real']):
            return round(random.uniform(0.0, 100.0), 2)
        
        elif any(t in col_type for t in ['bool', 'boolean']):
            return random.choice([True, False])
        
        elif any(t in col_type for t in ['text', 'varchar', 'char', 'string']):
            if 'id' in col_name:
                return f"{col_name}_{index + 1}"
            else:
                return f"Sample {col_name} {index + 1}"
        
        elif any(t in col_type for t in ['date', 'time']):
            return datetime.utcnow() - timedelta(days=random.randint(0, 365))
        
        # Default fallback
        else:
            return f"value_{index + 1}"


def create_sample_database(db_path: str = None, 
                          tables: Optional[List[str]] = None, 
                          records_per_table: int = 20) -> Dict[str, int]:
    """
    Create sample data for any database schema.
    
    Args:
        db_path: Database path (uses config if None)
        tables: Specific tables to populate (None = all tables)
        records_per_table: Number of records per table
        
    Returns:
        Dictionary with table names and record counts
    """
    generator = GenericSampleDataGenerator()
    return generator.create_sample_database(tables, records_per_table)


# For backward compatibility and direct execution
if __name__ == "__main__":
    result = create_sample_database()
    print(f"Created sample data: {result}")