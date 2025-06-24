"""
Query optimizer for Text-to-SQL agent.
Optimizes generated SQL queries for better performance and readability.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging

from ..config import config
from .schema_inspector import schema_inspector

logger = logging.getLogger(__name__)


@dataclass
class OptimizationSuggestion:
    """Represents a query optimization suggestion."""
    type: str  # "performance", "readability", "safety"
    priority: str  # "low", "medium", "high"
    description: str
    original_pattern: str
    suggested_replacement: str
    explanation: str


class QueryOptimizer:
    """
    Advanced query optimizer for SQL queries.
    
    Optimizations include:
    1. Performance improvements
    2. Readability enhancements
    3. Best practice enforcement
    4. Index utilization hints
    5. Query structure improvements
    """
    
    def __init__(self):
        self.schema_inspector = schema_inspector
    
    def optimize_query(self, sql_query: str, table_context: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Optimize SQL query and return optimized version with suggestions.
        
        Returns:
            Dict with optimized_query, suggestions, and performance_score
        """
        if not sql_query or not sql_query.strip():
            return {
                "optimized_query": sql_query,
                "suggestions": [],
                "performance_score": 0.0,
                "readability_score": 0.0,
                "optimization_applied": False
            }
        
        # Start with the original query
        optimized_query = sql_query.strip()
        suggestions = []
        
        # Apply various optimization techniques
        optimized_query, perf_suggestions = self._optimize_performance(optimized_query, table_context)
        suggestions.extend(perf_suggestions)
        
        optimized_query, read_suggestions = self._optimize_readability(optimized_query)
        suggestions.extend(read_suggestions)
        
        optimized_query, struct_suggestions = self._optimize_structure(optimized_query)
        suggestions.extend(struct_suggestions)
        
        # Calculate scores
        performance_score = self._calculate_performance_score(optimized_query, table_context)
        readability_score = self._calculate_readability_score(optimized_query)
        
        return {
            "optimized_query": optimized_query,
            "suggestions": suggestions,
            "performance_score": performance_score,
            "readability_score": readability_score,
            "optimization_applied": len(suggestions) > 0
        }
    
    def _optimize_performance(self, query: str, table_context: Optional[List[str]] = None) -> Tuple[str, List[OptimizationSuggestion]]:
        """Apply performance optimizations."""
        optimized = query
        suggestions = []
        
        # 1. Add LIMIT if missing and no aggregation
        if not re.search(r'\bLIMIT\b', optimized, re.IGNORECASE):
            has_aggregation = bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX|GROUP\s+BY)\b', optimized, re.IGNORECASE))
            if not has_aggregation:
                # Add a reasonable LIMIT
                limit_value = min(config.safety.max_result_rows, 100)
                optimized = f"{optimized.rstrip(';')} LIMIT {limit_value};"
                
                suggestions.append(OptimizationSuggestion(
                    type="performance",
                    priority="high",
                    description="Added LIMIT clause",
                    original_pattern="Query without LIMIT",
                    suggested_replacement=f"Added LIMIT {limit_value}",
                    explanation="LIMIT prevents accidentally retrieving large result sets"
                ))
        
        # 2. Replace SELECT * with specific columns when possible
        if 'SELECT *' in optimized.upper():
            if table_context:
                specific_columns = self._suggest_specific_columns(query, table_context)
                if specific_columns:
                    column_list = ', '.join(specific_columns[:10])  # Limit to 10 columns
                    optimized = re.sub(r'SELECT\s+\*', f'SELECT {column_list}', optimized, flags=re.IGNORECASE)
                    
                    suggestions.append(OptimizationSuggestion(
                        type="performance",
                        priority="medium",
                        description="Replaced SELECT * with specific columns",
                        original_pattern="SELECT *",
                        suggested_replacement=f"SELECT {column_list}",
                        explanation="Specific columns reduce network traffic and improve performance"
                    ))
        
        # 3. Optimize JOIN order (put smaller tables first when possible)
        optimized, join_suggestions = self._optimize_joins(optimized, table_context)
        suggestions.extend(join_suggestions)
        
        # 4. Suggest indexes for WHERE conditions
        index_suggestions = self._suggest_indexes(optimized, table_context)
        suggestions.extend(index_suggestions)
        
        # 5. Optimize LIKE patterns
        optimized, like_suggestions = self._optimize_like_patterns(optimized)
        suggestions.extend(like_suggestions)
        
        return optimized, suggestions
    
    def _optimize_readability(self, query: str) -> Tuple[str, List[OptimizationSuggestion]]:
        """Apply readability optimizations."""
        optimized = query
        suggestions = []
        
        # 1. Format SQL keywords
        optimized = self._format_sql_keywords(optimized)
        
        # 2. Add proper indentation and line breaks
        if len(optimized) > 100:  # Only format longer queries
            formatted = self._format_sql_structure(optimized)
            if formatted != optimized:
                suggestions.append(OptimizationSuggestion(
                    type="readability",
                    priority="low",
                    description="Improved SQL formatting",
                    original_pattern="Compact formatting",
                    suggested_replacement="Multi-line formatting with indentation",
                    explanation="Better formatting improves query readability and maintainability"
                ))
                optimized = formatted
        
        # 3. Add table aliases for readability
        optimized, alias_suggestions = self._add_table_aliases(optimized)
        suggestions.extend(alias_suggestions)
        
        return optimized, suggestions
    
    def _optimize_structure(self, query: str) -> Tuple[str, List[OptimizationSuggestion]]:
        """Apply structural optimizations."""
        optimized = query
        suggestions = []
        
        # 1. Convert implicit joins to explicit JOINs
        optimized, join_suggestions = self._convert_to_explicit_joins(optimized)
        suggestions.extend(join_suggestions)
        
        # 2. Optimize IN clauses with EXISTS
        optimized, exists_suggestions = self._optimize_in_clauses(optimized)
        suggestions.extend(exists_suggestions)
        
        # 3. Optimize NOT IN with LEFT JOIN
        optimized, not_in_suggestions = self._optimize_not_in_clauses(optimized)
        suggestions.extend(not_in_suggestions)
        
        return optimized, suggestions
    
    def _suggest_specific_columns(self, query: str, tables: List[str]) -> Optional[List[str]]:
        """Suggest specific columns to replace SELECT *."""
        if not tables:
            return None
        
        suggested_columns = []
        
        for table_name in tables:
            table_info = self.schema_inspector.get_table_info(table_name, include_sample_data=False)
            if table_info:
                # Prioritize important columns
                for col in table_info.columns:
                    if col.primary_key:
                        suggested_columns.append(f"{table_name}.{col.name}")
                    elif col.name.lower() in ['name', 'title', 'description', 'email', 'status']:
                        suggested_columns.append(f"{table_name}.{col.name}")
                
                # Add a few more common columns
                for col in table_info.columns[:5]:  # First 5 columns
                    col_ref = f"{table_name}.{col.name}"
                    if col_ref not in suggested_columns:
                        suggested_columns.append(col_ref)
        
        return suggested_columns[:10]  # Limit to 10 columns
    
    def _optimize_joins(self, query: str, table_context: Optional[List[str]] = None) -> Tuple[str, List[OptimizationSuggestion]]:
        """Optimize JOIN operations."""
        suggestions = []
        
        # For now, just suggest proper JOIN syntax if using WHERE-based joins
        if re.search(r'WHERE.*=.*\..*', query, re.IGNORECASE):
            suggestions.append(OptimizationSuggestion(
                type="performance",
                priority="medium",
                description="Consider using explicit JOIN syntax",
                original_pattern="WHERE table1.col = table2.col",
                suggested_replacement="JOIN table2 ON table1.col = table2.col",
                explanation="Explicit JOINs are more readable and often perform better"
            ))
        
        return query, suggestions
    
    def _suggest_indexes(self, query: str, table_context: Optional[List[str]] = None) -> List[OptimizationSuggestion]:
        """Suggest indexes for WHERE conditions."""
        suggestions = []
        
        # Extract WHERE conditions
        where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
        if where_match and table_context:
            where_clause = where_match.group(1)
            
            # Find column references in WHERE clause
            column_pattern = r'(\w+)\.(\w+)\s*[=<>]'
            matches = re.findall(column_pattern, where_clause)
            
            for table, column in matches:
                if table in table_context:
                    suggestions.append(OptimizationSuggestion(
                        type="performance",
                        priority="low",
                        description=f"Consider index on {table}.{column}",
                        original_pattern=f"WHERE {table}.{column}",
                        suggested_replacement=f"CREATE INDEX idx_{table}_{column} ON {table}({column})",
                        explanation="Indexes on WHERE clause columns can significantly improve query performance"
                    ))
        
        return suggestions
    
    def _optimize_like_patterns(self, query: str) -> Tuple[str, List[OptimizationSuggestion]]:
        """Optimize LIKE patterns."""
        suggestions = []
        
        # Check for leading wildcard patterns
        if re.search(r"LIKE\s+['\"]%", query, re.IGNORECASE):
            suggestions.append(OptimizationSuggestion(
                type="performance",
                priority="medium",
                description="Leading wildcard LIKE pattern detected",
                original_pattern="LIKE '%pattern'",
                suggested_replacement="Consider full-text search or different approach",
                explanation="Leading wildcards prevent index usage and can be slow"
            ))
        
        return query, suggestions
    
    def _format_sql_keywords(self, query: str) -> str:
        """Format SQL keywords consistently."""
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
            'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'UNION',
            'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'LIKE', 'BETWEEN', 'IS', 'NULL',
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 'AS'
        ]
        
        formatted = query
        for keyword in keywords:
            # Replace keyword with uppercase version (case-insensitive)
            pattern = r'\b' + re.escape(keyword) + r'\b'
            formatted = re.sub(pattern, keyword.upper(), formatted, flags=re.IGNORECASE)
        
        return formatted
    
    def _format_sql_structure(self, query: str) -> str:
        """Format SQL with proper indentation and line breaks."""
        # Basic formatting - add line breaks before major clauses
        formatted = query
        
        # Add line breaks before major keywords
        major_keywords = ['FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT']
        for keyword in major_keywords:
            pattern = r'\s+' + keyword + r'\b'
            replacement = f'\n{keyword}'
            formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
        
        # Indent JOIN clauses
        formatted = re.sub(r'\n((?:INNER|LEFT|RIGHT|FULL)?\s*JOIN)', r'\n  \1', formatted, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        formatted = re.sub(r'\n\s*\n', '\n', formatted)
        formatted = formatted.strip()
        
        return formatted
    
    def _add_table_aliases(self, query: str) -> Tuple[str, List[OptimizationSuggestion]]:
        """Add table aliases for better readability."""
        suggestions = []
        
        # Count table references
        table_count = len(re.findall(r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)', query, re.IGNORECASE))
        
        if table_count > 1 and not re.search(r'\b\w+\s+AS\s+\w+\b|\b\w+\s+\w+\b', query):
            suggestions.append(OptimizationSuggestion(
                type="readability",
                priority="low",
                description="Consider adding table aliases",
                original_pattern="Full table names in multi-table query",
                suggested_replacement="Use aliases like 'e' for employees, 'd' for departments",
                explanation="Table aliases make complex queries more readable"
            ))
        
        return query, suggestions
    
    def _convert_to_explicit_joins(self, query: str) -> Tuple[str, List[OptimizationSuggestion]]:
        """Convert implicit joins to explicit JOIN syntax."""
        suggestions = []
        
        # Check for comma-separated tables in FROM clause
        if re.search(r'FROM\s+\w+\s*,\s*\w+', query, re.IGNORECASE):
            suggestions.append(OptimizationSuggestion(
                type="readability",
                priority="medium",
                description="Convert implicit joins to explicit JOIN syntax",
                original_pattern="FROM table1, table2 WHERE table1.id = table2.id",
                suggested_replacement="FROM table1 JOIN table2 ON table1.id = table2.id",
                explanation="Explicit JOINs are more readable and less error-prone"
            ))
        
        return query, suggestions
    
    def _optimize_in_clauses(self, query: str) -> Tuple[str, List[OptimizationSuggestion]]:
        """Optimize IN clauses with EXISTS when appropriate."""
        suggestions = []
        
        # Check for IN with subqueries
        if re.search(r'\bIN\s*\(\s*SELECT\b', query, re.IGNORECASE):
            suggestions.append(OptimizationSuggestion(
                type="performance",
                priority="low",
                description="Consider using EXISTS instead of IN with subquery",
                original_pattern="WHERE col IN (SELECT ...)",
                suggested_replacement="WHERE EXISTS (SELECT 1 FROM ... WHERE ...)",
                explanation="EXISTS can be more efficient than IN with subqueries"
            ))
        
        return query, suggestions
    
    def _optimize_not_in_clauses(self, query: str) -> Tuple[str, List[OptimizationSuggestion]]:
        """Optimize NOT IN clauses."""
        suggestions = []
        
        if re.search(r'\bNOT\s+IN\b', query, re.IGNORECASE):
            suggestions.append(OptimizationSuggestion(
                type="performance",
                priority="medium",
                description="Consider using LEFT JOIN with NULL check instead of NOT IN",
                original_pattern="WHERE col NOT IN (SELECT ...)",
                suggested_replacement="LEFT JOIN ... ON ... WHERE foreign_key IS NULL",
                explanation="LEFT JOIN with NULL check is often faster than NOT IN"
            ))
        
        return query, suggestions
    
    def _calculate_performance_score(self, query: str, table_context: Optional[List[str]] = None) -> float:
        """Calculate performance score (0.0 to 1.0)."""
        score = 1.0
        query_upper = query.upper()
        
        # Deduct points for performance issues
        if 'SELECT *' in query_upper:
            score -= 0.2
        
        if not re.search(r'\bLIMIT\b', query_upper):
            score -= 0.3
        
        if re.search(r'LIKE\s+[\'"]%', query):
            score -= 0.2
        
        if re.search(r'\bNOT\s+IN\b', query_upper):
            score -= 0.1
        
        # Count complexity factors
        subquery_count = len(re.findall(r'\(\s*SELECT\b', query_upper))
        if subquery_count > 2:
            score -= 0.1 * (subquery_count - 2)
        
        join_count = len(re.findall(r'\bJOIN\b', query_upper))
        if join_count > 3:
            score -= 0.05 * (join_count - 3)
        
        return max(0.0, score)
    
    def _calculate_readability_score(self, query: str) -> float:
        """Calculate readability score (0.0 to 1.0)."""
        score = 1.0
        
        # Check formatting
        if len(query) > 100 and '\n' not in query:
            score -= 0.3  # Long query without line breaks
        
        # Check for consistent keyword casing
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'ORDER', 'GROUP']
        mixed_case = False
        for keyword in keywords:
            if keyword.lower() in query and keyword.upper() in query:
                mixed_case = True
                break
        
        if mixed_case:
            score -= 0.2
        
        # Check for table aliases in multi-table queries
        table_count = len(re.findall(r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)', query, re.IGNORECASE))
        has_aliases = bool(re.search(r'\b\w+\s+AS\s+\w+\b|\b\w+\s+[a-z]\b', query, re.IGNORECASE))
        
        if table_count > 1 and not has_aliases:
            score -= 0.1
        
        return max(0.0, score)


# Create global query optimizer instance
query_optimizer = QueryOptimizer()