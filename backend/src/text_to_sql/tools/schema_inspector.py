"""
Advanced schema inspector for Text-to-SQL agent.
Improved version addressing the limitations of the original sql-agent schema extraction.
"""
import sqlite3
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import re
import logging

from ..config import config
from .database_toolkit import db_toolkit

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Enhanced column information."""
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default_value: Optional[str] = None
    unique: bool = False
    auto_increment: bool = False
    description: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    """Foreign key relationship information."""
    column: str
    referenced_table: str
    referenced_column: str
    on_delete: Optional[str] = None
    on_update: Optional[str] = None


@dataclass
class TableInfo:
    """Complete table information."""
    name: str
    columns: List[ColumnInfo]
    foreign_keys: List[ForeignKeyInfo]
    row_count: Optional[int] = None
    sample_data: Optional[List[Dict]] = None
    description: Optional[str] = None


class SchemaInspector:
    """
    Advanced schema inspector that addresses the original sql-agent limitations.
    
    Improvements:
    1. Better type detection and normalization
    2. Relationship discovery and mapping
    3. Sample data extraction with intelligent selection
    4. Semantic analysis of table/column names
    5. Query relevance scoring
    """
    
    def __init__(self):
        self.db_toolkit = db_toolkit
        self._schema_cache = {}
        self._cache_timestamp = None
        
    def get_all_tables_info(self, include_sample_data: bool = True) -> Dict[str, TableInfo]:
        """Get comprehensive information for all tables."""
        if self._should_refresh_cache():
            self._refresh_schema_cache(include_sample_data)
        
        return self._schema_cache.copy()
    
    def get_table_info(self, table_name: str, include_sample_data: bool = True) -> Optional[TableInfo]:
        """Get information for a specific table."""
        all_tables = self.get_all_tables_info(include_sample_data)
        return all_tables.get(table_name)
    
    def get_relevant_tables(self, query: str, max_tables: int = None) -> List[str]:
        """
        Determine which tables are most relevant for a given query.
        
        Improved algorithm that considers:
        1. Direct table/column mentions
        2. Semantic similarity
        3. Relationship proximity
        4. Data availability
        """
        max_tables = max_tables or config.agent.max_relevant_tables
        query_lower = query.lower()
        
        all_tables = self.get_all_tables_info(include_sample_data=False)
        table_scores = {}
        
        for table_name, table_info in all_tables.items():
            score = self._calculate_table_relevance(query_lower, table_name, table_info)
            table_scores[table_name] = score
        
        # Sort by relevance score and return top tables
        sorted_tables = sorted(
            table_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        relevant_tables = []
        for table_name, score in sorted_tables:
            if score >= config.agent.relevance_threshold:
                relevant_tables.append(table_name)
            if len(relevant_tables) >= max_tables:
                break
        
        # If no tables meet threshold, return top-scoring tables
        if not relevant_tables:
            relevant_tables = [table for table, _ in sorted_tables[:max_tables]]
        
        # Add related tables if we have space
        if len(relevant_tables) < max_tables:
            related_tables = self._get_related_tables(relevant_tables, all_tables)
            for related_table in related_tables:
                if related_table not in relevant_tables and len(relevant_tables) < max_tables:
                    relevant_tables.append(related_table)
        
        logger.info(f"Selected relevant tables for query '{query[:50]}...': {relevant_tables}")
        return relevant_tables
    
    def format_schema_for_llm(self, table_names: Optional[List[str]] = None, 
                            include_sample_data: bool = True) -> str:
        """Format schema information optimized for LLM consumption."""
        all_tables = self.get_all_tables_info(include_sample_data)
        
        if table_names:
            tables_to_format = {name: all_tables[name] for name in table_names if name in all_tables}
        else:
            tables_to_format = all_tables
        
        formatted_parts = []
        
        for table_name, table_info in tables_to_format.items():
            parts = [f"## Table: {table_name}"]
            
            if table_info.description:
                parts.append(f"Description: {table_info.description}")
            
            if table_info.row_count is not None:
                parts.append(f"Rows: {table_info.row_count:,}")
            
            # Columns with enhanced formatting
            parts.append("\n### Columns:")
            for col in table_info.columns:
                col_desc = f"- **{col.name}**: {col.type}"
                
                attributes = []
                if col.primary_key:
                    attributes.append("PRIMARY KEY")
                if col.auto_increment:
                    attributes.append("AUTO_INCREMENT")
                if not col.nullable:
                    attributes.append("NOT NULL")
                if col.unique:
                    attributes.append("UNIQUE")
                if col.default_value:
                    attributes.append(f"DEFAULT: {col.default_value}")
                
                if attributes:
                    col_desc += f" ({', '.join(attributes)})"
                
                if col.description:
                    col_desc += f" - {col.description}"
                
                parts.append(col_desc)
            
            # Foreign key relationships
            if table_info.foreign_keys:
                parts.append("\n### Relationships:")
                for fk in table_info.foreign_keys:
                    fk_desc = f"- {fk.column} → {fk.referenced_table}.{fk.referenced_column}"
                    if fk.on_delete or fk.on_update:
                        constraints = []
                        if fk.on_delete:
                            constraints.append(f"ON DELETE {fk.on_delete}")
                        if fk.on_update:
                            constraints.append(f"ON UPDATE {fk.on_update}")
                        fk_desc += f" ({', '.join(constraints)})"
                    parts.append(fk_desc)
            
            # Sample data with intelligent selection
            if include_sample_data and table_info.sample_data:
                parts.append(f"\n### Sample Data:")
                for i, row in enumerate(table_info.sample_data, 1):
                    # Format row data intelligently
                    row_items = []
                    for key, value in row.items():
                        if value is None:
                            row_items.append(f"{key}=NULL")
                        elif isinstance(value, str) and len(value) > 50:
                            row_items.append(f"{key}='{value[:47]}...'")
                        else:
                            row_items.append(f"{key}={value}")
                    
                    parts.append(f"{i}. {', '.join(row_items)}")
            
            formatted_parts.append("\n".join(parts))
        
        return "\n\n".join(formatted_parts)
    
    def get_table_relationships(self) -> Dict[str, Dict[str, List[str]]]:
        """Get relationship mapping between all tables."""
        all_tables = self.get_all_tables_info(include_sample_data=False)
        relationships = {}
        
        for table_name, table_info in all_tables.items():
            relationships[table_name] = {
                'references': [],      # Tables this table references
                'referenced_by': [],   # Tables that reference this table
                'related': []          # Tables with shared columns/patterns
            }
            
            # Direct foreign key relationships
            for fk in table_info.foreign_keys:
                relationships[table_name]['references'].append(fk.referenced_table)
            
            # Find tables that reference this table
            for other_table, other_info in all_tables.items():
                if other_table == table_name:
                    continue
                for fk in other_info.foreign_keys:
                    if fk.referenced_table == table_name:
                        relationships[table_name]['referenced_by'].append(other_table)
            
            # Find semantically related tables
            related_tables = self._find_semantically_related_tables(table_name, all_tables)
            relationships[table_name]['related'] = related_tables
        
        return relationships
    
    def _should_refresh_cache(self) -> bool:
        """Check if schema cache should be refreshed."""
        if not config.agent.cache_schema:
            return True
        
        if not self._schema_cache or not self._cache_timestamp:
            return True
        
        import time
        cache_age = time.time() - self._cache_timestamp
        return cache_age > config.agent.cache_ttl_seconds
    
    def _refresh_schema_cache(self, include_sample_data: bool = True):
        """Refresh the schema cache."""
        import time
        
        logger.info("Refreshing schema cache...")
        self._schema_cache = {}
        
        table_names = self.db_toolkit.get_table_names()
        
        for table_name in table_names:
            try:
                table_info = self._extract_table_info(table_name, include_sample_data)
                self._schema_cache[table_name] = table_info
            except Exception as e:
                logger.error(f"Failed to extract info for table {table_name}: {str(e)}")
        
        self._cache_timestamp = time.time()
        logger.info(f"Schema cache refreshed with {len(self._schema_cache)} tables")
    
    def _extract_table_info(self, table_name: str, include_sample_data: bool = True) -> TableInfo:
        """Extract comprehensive table information."""
        try:
            # Get basic table info from database toolkit
            db_info = self.db_toolkit.get_table_info(table_name)
            
            if not db_info:
                logger.warning(f"No database info found for table {table_name}")
                return None
            
            # Process columns
            columns = []
            for col_info in db_info.get('columns', []):
                column = ColumnInfo(
                    name=col_info['name'],
                    type=self._normalize_type(col_info['type']),
                    nullable=not bool(col_info['notnull']),
                    primary_key=bool(col_info['pk']),
                    default_value=col_info['dflt_value'],
                    unique=False,  # Would need additional query to determine
                    auto_increment=False,  # Would need additional logic
                    description=self._infer_column_description(col_info['name'])
                )
                columns.append(column)
            
            # Process foreign keys
            foreign_keys = []
            for fk_info in db_info.get('foreign_keys', []):
                fk = ForeignKeyInfo(
                    column=fk_info['from'],
                    referenced_table=fk_info['table'],
                    referenced_column=fk_info['to'],
                    on_delete=fk_info['on_delete'],
                    on_update=fk_info['on_update']
                )
                foreign_keys.append(fk)
            
            # Get sample data if requested
            sample_data = None
            if include_sample_data:
                sample_data = self.db_toolkit.get_sample_data(table_name)
            
            return TableInfo(
                name=table_name,
                columns=columns,
                foreign_keys=foreign_keys,
                row_count=db_info.get('row_count'),
                sample_data=sample_data,
                description=self._infer_table_description(table_name)
            )
            
        except Exception as e:
            logger.error(f"Failed to extract info for table {table_name}: {str(e)}")
            return None
    
    def _calculate_table_relevance(self, query: str, table_name: str, table_info: TableInfo) -> float:
        """Calculate relevance score for a table given a query."""
        score = 0.0
        
        # Direct table name mention (highest score)
        if table_name.lower() in query:
            score += 1.0
        
        # Partial table name matches
        table_words = re.split(r'[_\s]+', table_name.lower())
        for word in table_words:
            if word in query and len(word) > 2:
                score += 0.3
        
        # Column name mentions
        column_matches = 0
        for col in table_info.columns:
            if col.name.lower() in query:
                column_matches += 1
                score += 0.2
                
                # Bonus for primary key or unique columns
                if col.primary_key:
                    score += 0.1
        
        # Semantic keyword matching
        semantic_scores = self._get_semantic_scores(query, table_name, table_info)
        score += semantic_scores
        
        # Bonus for tables with data
        if table_info.row_count and table_info.row_count > 0:
            score += 0.1
        
        # Penalty for very large tables (might be less relevant for exploration)
        if table_info.row_count and table_info.row_count > 100000:
            score -= 0.05
        
        return score
    
    def _get_semantic_scores(self, query: str, table_name: str, table_info: TableInfo) -> float:
        """Calculate semantic relevance scores."""
        score = 0.0
        
        # Domain-specific keyword mappings
        keyword_mappings = {
            # Employee/HR domain
            ('employee', 'staff', 'worker', 'person', 'people'): ['employees', 'staff', 'personnel'],
            ('department', 'division', 'team'): ['departments', 'divisions', 'teams'],
            ('salary', 'wage', 'pay', 'compensation'): ['employees', 'payroll', 'compensation'],
            
            # Customer/Sales domain
            ('customer', 'client', 'buyer'): ['customers', 'clients', 'users'],
            ('order', 'purchase', 'transaction'): ['orders', 'transactions', 'purchases'],
            ('product', 'item', 'goods'): ['products', 'items', 'inventory'],
            ('sale', 'revenue', 'income'): ['sales', 'orders', 'transactions'],
            
            # Infrastructure domain
            ('server', 'machine', 'host'): ['servers', 'hosts', 'machines', 'backend_servers'],
            ('load balancer', 'lb', 'balancer'): ['load_balancers', 'balancers'],
            ('network', 'datacenter', 'dc'): ['datacenters', 'networks'],
            ('vip', 'virtual ip'): ['vip_pools', 'vips'],
            
            # General database terms
            ('user', 'account'): ['users', 'accounts', 'customers'],
            ('log', 'event', 'audit'): ['logs', 'events', 'audit_trail'],
            ('config', 'setting', 'parameter'): ['config', 'settings', 'parameters']
        }
        
        query_lower = query.lower()
        table_name_lower = table_name.lower()
        
        for keywords, table_patterns in keyword_mappings.items():
            if any(keyword in query_lower for keyword in keywords):
                if any(pattern in table_name_lower for pattern in table_patterns):
                    score += 0.4
        
        return score
    
    def _get_related_tables(self, primary_tables: List[str], all_tables: Dict[str, TableInfo]) -> List[str]:
        """Find tables related to the primary relevant tables."""
        related_tables = []
        relationships = self.get_table_relationships()
        
        for table_name in primary_tables:
            if table_name in relationships:
                # Add directly referenced tables
                related_tables.extend(relationships[table_name]['references'])
                # Add tables that reference this one
                related_tables.extend(relationships[table_name]['referenced_by'])
                # Add semantically related tables
                related_tables.extend(relationships[table_name]['related'])
        
        # Remove duplicates and primary tables
        related_tables = list(set(related_tables) - set(primary_tables))
        return related_tables
    
    def _find_semantically_related_tables(self, table_name: str, all_tables: Dict[str, TableInfo]) -> List[str]:
        """Find tables semantically related to the given table."""
        related = []
        table_info = all_tables[table_name]
        
        for other_name, other_info in all_tables.items():
            if other_name == table_name:
                continue
            
            # Check for similar column names
            table_columns = {col.name.lower() for col in table_info.columns}
            other_columns = {col.name.lower() for col in other_info.columns}
            
            # Calculate column overlap
            common_columns = table_columns & other_columns
            if len(common_columns) >= 2:  # At least 2 common columns
                related.append(other_name)
            
            # Check for naming patterns (e.g., order -> order_items)
            if (table_name.lower() in other_name.lower() or 
                other_name.lower() in table_name.lower()):
                if other_name not in related:
                    related.append(other_name)
        
        return related
    
    def _normalize_type(self, raw_type: str) -> str:
        """Normalize SQL types to standard forms."""
        if not raw_type:
            return "TEXT"
        
        type_mapping = {
            'INTEGER': 'INTEGER',
            'TEXT': 'TEXT', 
            'REAL': 'REAL',
            'BLOB': 'BLOB',
            'NUMERIC': 'NUMERIC',
            'VARCHAR': 'TEXT',
            'CHAR': 'TEXT',
            'CHARACTER': 'TEXT',
            'DECIMAL': 'NUMERIC',
            'FLOAT': 'REAL',
            'DOUBLE': 'REAL',
            'BOOLEAN': 'INTEGER',
            'BOOL': 'INTEGER',
            'DATE': 'TEXT',
            'DATETIME': 'TEXT',
            'TIMESTAMP': 'TEXT',
            'TIME': 'TEXT'
        }
        
        # Extract base type (remove size constraints)
        base_type = str(raw_type).upper().split('(')[0].strip()
        return type_mapping.get(base_type, base_type)
    
    def _infer_table_description(self, table_name: str) -> str:
        """Infer a description for the table based on its name."""
        descriptions = {
            'employees': 'Employee information and HR data',
            'departments': 'Department organization and structure',
            'customers': 'Customer profiles and contact information',
            'orders': 'Customer orders and transactions',
            'products': 'Product catalog and inventory',
            'order_items': 'Individual items within orders',
            'load_balancers': 'Load balancer devices and configuration',
            'vip_pools': 'Virtual IP pools and services',
            'backend_servers': 'Backend servers and health status',
            'datacenters': 'Data center locations and capacity'
        }
        
        return descriptions.get(table_name.lower(), f"Data table: {table_name}")
    
    def _infer_column_description(self, column_name: str) -> str:
        """Infer a description for the column based on its name."""
        descriptions = {
            'id': 'Unique identifier',
            'name': 'Name or title',
            'email': 'Email address',
            'phone': 'Phone number',
            'address': 'Physical address',
            'created_date': 'Record creation date',
            'updated_date': 'Last update date',
            'status': 'Current status',
            'price': 'Price amount',
            'cost': 'Cost amount',
            'quantity': 'Quantity or count',
            'description': 'Detailed description'
        }
        
        column_lower = column_name.lower()
        
        # Check for exact matches
        if column_lower in descriptions:
            return descriptions[column_lower]
        
        # Check for pattern matches
        if 'id' in column_lower and column_lower.endswith('id'):
            return f"Foreign key reference"
        elif 'date' in column_lower:
            return "Date/time value"
        elif 'count' in column_lower or 'num' in column_lower:
            return "Numeric count or quantity"
        elif 'url' in column_lower or 'uri' in column_lower:
            return "Web URL or URI"
        
        return None


# Global instance for easy importing
schema_inspector = SchemaInspector()