"""
Safety validator for Text-to-SQL agent.
Validates SQL queries for security and safety.
"""
import re
from typing import List, Tuple
import logging

from ...common.config import config
from ..pipeline.state import ValidationResult

logger = logging.getLogger(__name__)


class SafetyValidator:
    """
    SQL query safety validator.
    
    Validates queries for:
    1. Blocked operations (INSERT, UPDATE, DELETE, etc.)
    2. Blocked table/column access
    3. SQL injection patterns
    4. Performance issues (warnings only)
    """
    
    def __init__(self):
        self.blocked_keywords = set(word.upper() for word in config.safety.blocked_keywords)
        self.blocked_tables = set(config.safety.blocked_tables)
        self.blocked_columns = config.safety.blocked_columns
    
    def validate_query(self, sql_query: str) -> ValidationResult:
        """
        Validate SQL query for safety.
        
        Returns ValidationResult with safety assessment.
        """
        # Normalize query for analysis
        normalized_query = self._normalize_query(sql_query)
        
        errors = []
        warnings = []
        
        # 1. Check for blocked operations
        operation_errors = self._check_blocked_operations(normalized_query)
        errors.extend(operation_errors)
        
        # 2. Check for blocked tables and columns
        table_errors, allowed_tables = self._check_blocked_tables(normalized_query)
        errors.extend(table_errors)
        
        # 3. Check for SQL injection patterns
        injection_errors = self._check_injection_patterns(sql_query)
        errors.extend(injection_errors)
        
        # 4. Basic performance warnings
        perf_warnings = self._check_performance_issues(normalized_query)
        warnings.extend(perf_warnings)
        
        # Determine validity
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            allowed_tables=allowed_tables
        )
    
    def _normalize_query(self, sql_query: str) -> str:
        """Normalize SQL query for analysis."""
        # Remove comments
        sql_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
        sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
        
        # Normalize whitespace
        sql_query = re.sub(r'\s+', ' ', sql_query.strip())
        
        return sql_query
    
    def _check_blocked_operations(self, query: str) -> List[str]:
        """Check for blocked SQL operations."""
        errors = []
        query_upper = query.upper()
        
        # Check for blocked keywords
        words = re.findall(r'\b[A-Z_]+\b', query_upper)
        
        for word in words:
            if word in self.blocked_keywords:
                errors.append(f"Blocked keyword: {word}")
        
        # Check for dangerous patterns
        dangerous_patterns = [
            (r'\bEXEC\b|\bEXECUTE\b', "Dynamic SQL execution"),
            (r'\bxp_\w+|\bsp_\w+', "System stored procedures"),
            (r'\bINTO\s+OUTFILE\b|\bLOAD_FILE\b', "File operations"),
            (r';.*(?:SELECT|INSERT|UPDATE|DELETE)', "Multiple statements"),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, query_upper):
                errors.append(f"Dangerous pattern: {description}")
        
        return errors
    
    def _check_blocked_tables(self, query: str) -> Tuple[List[str], List[str]]:
        """Check for access to blocked tables and columns."""
        errors = []
        allowed_tables = []
        
        # Extract table names (simplified)
        table_matches = re.findall(r'\b(?:FROM|JOIN)\s+(\w+)', query, re.IGNORECASE)
        tables_in_query = [table.lower() for table in table_matches]
        
        # Check against blocked tables
        for table in tables_in_query:
            if table in self.blocked_tables:
                errors.append(f"Access to table '{table}' is blocked")
            else:
                allowed_tables.append(table)
        
        # Check for blocked column patterns
        for pattern in self.blocked_columns:
            if re.search(rf'\b{pattern}\b', query, re.IGNORECASE):
                errors.append(f"Access to sensitive columns matching '{pattern}' is blocked")
        
        return errors, allowed_tables
    
    def _check_injection_patterns(self, query: str) -> List[str]:
        """Check for common SQL injection patterns."""
        errors = []
        
        # Key injection patterns to block (case-insensitive)
        injection_patterns = [
            (r'\bUNION\b.*\bSELECT\b.*\bFROM\b.*information_schema', 
             "Potential schema discovery attempt"),
            (r'\bOR\s+1\s*=\s*1|\bAND\s+1\s*=\s*1',
             "Potential SQL injection (always true condition)"),
            (r'\bSLEEP\s*\(|\bWAITFOR\s+DELAY|\bBENCHMARK\s*\(',
             "Time-based injection attempt"),
            (r';\s*(?:DROP|CREATE|ALTER)\s+(?:TABLE|DATABASE)',
             "DDL injection attempt"),
        ]
        
        for pattern, description in injection_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                errors.append(description)
        
        return errors
    
    def _check_performance_issues(self, query: str) -> List[str]:
        """Check for potential performance issues."""
        warnings = []
        
        # Basic performance checks (case-insensitive)
        if re.search(r'\bSELECT\s+\*\b', query, re.IGNORECASE):
            warnings.append("SELECT * may impact performance; specify needed columns")
        
        if not re.search(r'\bLIMIT\b|\bTOP\b', query, re.IGNORECASE):
            warnings.append("Consider adding LIMIT clause for large result sets")
        
        if re.search(r'\bLIKE\s+[\'"]%', query, re.IGNORECASE):
            warnings.append("Leading wildcard in LIKE may be slow")
        
        # Count joins
        join_count = len(re.findall(r'\bJOIN\b', query, re.IGNORECASE))
        if join_count > config.pipeline.max_safe_joins:
            warnings.append(f"High number of joins ({join_count}) may impact performance")
        
        return warnings
    

# Create global safety validator instance
safety_validator = SafetyValidator()