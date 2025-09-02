"""
Domain-agnostic SQLAlchemy schema inspector for any database.
Works automatically with any schema through reflection.
"""
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.engine import Engine, Inspector
from sqlalchemy.exc import SQLAlchemyError
import re

from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class TableRelevance:
    """Simple table relevance info."""
    table_name: str
    relevance_score: float
    reasons: List[str]
    column_matches: List[str]
    relationship_matches: List[str]


class SQLAlchemyInspector:
    """
    Domain-agnostic schema inspector using SQLAlchemy reflection.
    Works with any database schema automatically.
    
    Key advantages:
    1. Automatic schema discovery for any database
    2. Built-in relationship detection
    3. Column type inference
    4. Cross-database compatibility (SQLite, PostgreSQL, MySQL, etc.)
    5. No domain-specific assumptions
    """
    
    def __init__(self):
        """Initialize with SQLAlchemy engine and reflection."""
        self.engine: Optional[Engine] = None
        self.inspector: Optional[Inspector] = None
        self.metadata: Optional[MetaData] = None
        self._setup_engine()
    
    def _setup_engine(self):
        """Setup SQLAlchemy engine and inspector."""
        try:
            database_url = config.database.database_url
            self.engine = create_engine(database_url, echo=False)
            self.inspector = inspect(self.engine)
            self.metadata = MetaData()
            # Reflect all tables
            self.metadata.reflect(bind=self.engine)
            logger.info(f"Connected to database with {len(self.metadata.tables)} tables")
        except Exception as e:
            logger.error(f"Failed to setup SQLAlchemy engine: {e}")
            raise
    
    def get_relevant_tables(self, query: str, max_tables: int = 5) -> List[str]:
        """
        Get most relevant tables for a query using SQLAlchemy's intelligence.
        Much simpler than manual keyword mapping!
        """
        if not self.metadata:
            return []
        
        query_lower = query.lower()
        table_scores = []
        
        for table_name, table in self.metadata.tables.items():
            relevance = self._calculate_table_relevance(query_lower, table_name, table)
            if relevance.relevance_score > 0:
                table_scores.append((table_name, relevance.relevance_score, relevance.reasons))
        
        # Sort by relevance and return top N
        table_scores.sort(key=lambda x: x[1], reverse=True)
        return [name for name, score, reasons in table_scores[:max_tables]]
    
    def _calculate_table_relevance(self, query: str, table_name: str, table) -> TableRelevance:
        """Calculate table relevance using SQLAlchemy metadata."""
        score = 0.0
        reasons = []
        column_matches = []
        relationship_matches = []
        
        # 1. Direct table name matching
        table_name_lower = table_name.lower()
        query_words = set(re.findall(r'\b\w+\b', query))
        table_words = set(re.findall(r'\b\w+\b', table_name_lower))
        
        # Exact table name match
        if table_name_lower in query:
            score += 1.0
            reasons.append(f"Exact table name match: {table_name}")
        
        # Partial table name matches
        common_words = query_words.intersection(table_words)
        if common_words:
            score += len(common_words) * 0.3
            reasons.append(f"Table name words match: {common_words}")
        
        # 2. Column name matching (SQLAlchemy gives us all columns automatically)
        for column in table.columns:
            col_name_lower = column.name.lower()
            
            # Exact column match
            if col_name_lower in query:
                score += 0.5
                column_matches.append(column.name)
                reasons.append(f"Column match: {column.name}")
            
            # Partial column word matches
            col_words = set(re.findall(r'\b\w+\b', col_name_lower))
            col_common = query_words.intersection(col_words)
            if col_common:
                score += len(col_common) * 0.2
                column_matches.append(column.name)
                reasons.append(f"Column word match: {column.name} ({col_common})")
        
        # 3. Foreign key relationships (SQLAlchemy discovers these automatically!)
        for fk in table.foreign_keys:
            ref_table = fk.column.table.name
            ref_table_words = set(re.findall(r'\b\w+\b', ref_table.lower()))
            fk_common = query_words.intersection(ref_table_words)
            if fk_common:
                score += 0.4
                relationship_matches.append(ref_table)
                reasons.append(f"Related to {ref_table} via {fk.parent.name}")
        
        # 4. Generic query intent analysis (domain-agnostic)
        intent_patterns = {
            'status': ['status', 'state', 'active', 'enabled', 'disabled', 'available'],
            'metrics': ['count', 'sum', 'avg', 'average', 'total', 'max', 'min', 'value'],
            'temporal': ['date', 'time', 'created', 'updated', 'modified', 'recent', 'last'],
            'identification': ['id', 'name', 'title', 'code', 'key', 'identifier'],
            'description': ['description', 'details', 'info', 'comment', 'note', 'text'],
            'location': ['address', 'location', 'place', 'region', 'zone', 'area'],
            'contact': ['email', 'phone', 'contact', 'address', 'number'],
            'financial': ['price', 'cost', 'amount', 'total', 'balance', 'payment'],
            'quantity': ['quantity', 'amount', 'number', 'count', 'size', 'length']
        }
        
        for intent, keywords in intent_patterns.items():
            # Check if query contains intent keywords
            query_has_intent = any(keyword in query for keyword in keywords)
            if query_has_intent:
                # Check if table has columns matching this intent
                matching_columns = [col.name for col in table.columns 
                                  if any(keyword in col.name.lower() for keyword in keywords)]
                if matching_columns:
                    score += 0.3 * len(matching_columns)
                    reasons.append(f"Intent-column match: {intent} ({matching_columns[:3]})")
        
        return TableRelevance(
            table_name=table_name,
            relevance_score=min(score, 2.0),  # Cap at 2.0
            reasons=reasons,
            column_matches=column_matches,
            relationship_matches=relationship_matches
        )
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get detailed table schema using SQLAlchemy reflection."""
        if not self.metadata or table_name not in self.metadata.tables:
            return {}
        
        table = self.metadata.tables[table_name]
        
        # Get column information
        columns = []
        for column in table.columns:
            col_info = {
                'name': column.name,
                'type': str(column.type),
                'nullable': column.nullable,
                'primary_key': column.primary_key,
                'foreign_key': None
            }
            
            # Check for foreign keys
            for fk in column.foreign_keys:
                col_info['foreign_key'] = {
                    'references_table': fk.column.table.name,
                    'references_column': fk.column.name
                }
                break
            
            columns.append(col_info)
        
        # Get foreign key relationships
        foreign_keys = []
        for fk in table.foreign_keys:
            foreign_keys.append({
                'column': fk.parent.name,
                'references_table': fk.column.table.name,
                'references_column': fk.column.name
            })
        
        # Get sample data (optional)
        sample_data = self._get_sample_data(table_name, limit=3)
        
        return {
            'table_name': table_name,
            'columns': columns,
            'foreign_keys': foreign_keys,
            'sample_data': sample_data,
            'row_count': self._get_row_count(table_name)
        }
    
    def _get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample data from table."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.warning(f"Failed to get sample data for {table_name}: {e}")
            return []
    
    def _get_row_count(self, table_name: str) -> Optional[int]:
        """Get row count for table."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {e}")
            return None
    
    def get_all_tables_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information for all tables."""
        if not self.metadata:
            return {}
        
        tables_info = {}
        for table_name in self.metadata.tables:
            tables_info[table_name] = self.get_table_schema(table_name)
        
        return tables_info
    
    def get_related_tables(self, primary_table: str) -> List[str]:
        """Get tables related to primary table via foreign keys."""
        if not self.metadata or primary_table not in self.metadata.tables:
            return []
        
        related = set()
        table = self.metadata.tables[primary_table]
        
        # Tables this table references
        for fk in table.foreign_keys:
            related.add(fk.column.table.name)
        
        # Tables that reference this table
        for other_name, other_table in self.metadata.tables.items():
            if other_name == primary_table:
                continue
            for fk in other_table.foreign_keys:
                if fk.column.table.name == primary_table:
                    related.add(other_name)
        
        return list(related)
    
    def analyze_query_context(self, query: str) -> Dict[str, Any]:
        """Analyze query and provide intelligent context."""
        relevant_tables = self.get_relevant_tables(query, max_tables=10)
        
        context = {
            'query': query,
            'relevant_tables': relevant_tables,
            'table_relationships': {},
            'suggested_joins': [],
            'query_complexity': 'simple'
        }
        
        # Analyze relationships between relevant tables
        if len(relevant_tables) > 1:
            for table in relevant_tables[:3]:  # Top 3 tables
                related = self.get_related_tables(table)
                context['table_relationships'][table] = [
                    t for t in related if t in relevant_tables
                ]
        
        # Suggest joins based on relationships
        for table, related_tables in context['table_relationships'].items():
            for related in related_tables:
                if related in relevant_tables:
                    context['suggested_joins'].append(f"{table} -> {related}")
        
        # Determine query complexity
        if len(relevant_tables) > 3:
            context['query_complexity'] = 'complex'
        elif len(relevant_tables) > 1:
            context['query_complexity'] = 'moderate'
        
        return context


# Global instance (renamed for consistency)
schema_inspector = SQLAlchemyInspector()