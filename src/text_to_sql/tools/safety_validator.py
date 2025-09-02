"""
Safety validator for Text-to-SQL agent.
Comprehensive security and safety checks for SQL queries.
"""
import re
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass
import logging

from ..config import config
from ..pipeline.state import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class SecurityThreat:
    """Represents a security threat found in SQL."""
    threat_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    location: str
    suggestion: str


class SafetyValidator:
    """
    Comprehensive safety validator for SQL queries.
    
    Protects against:
    1. SQL injection attacks
    2. Data modification operations
    3. Dangerous system operations
    4. Performance risks
    5. Information disclosure
    """
    
    def __init__(self):
        self.blocked_keywords = set(word.upper() for word in config.safety.blocked_keywords)
        self.blocked_tables = set(config.safety.blocked_tables)
        self.blocked_columns = config.safety.blocked_columns
        self.allowed_operations = set(op.upper() for op in config.safety.allowed_operations)
    
    def validate_query(self, sql_query: str) -> ValidationResult:
        """
        Perform comprehensive validation of SQL query.
        
        Returns ValidationResult with detailed safety assessment.
        """
        if not sql_query or not sql_query.strip():
            return ValidationResult(
                is_valid=False,
                errors=["Empty query provided"],
                warnings=[],
                safety_score=0.0,
                blocked_operations=[],
                allowed_tables=[],
                syntax_valid=False
            )
        
        # Normalize query for analysis
        normalized_query = self._normalize_query(sql_query)
        
        errors = []
        warnings = []
        blocked_operations = []
        threats = []
        
        # 1. Basic syntax and structure validation
        syntax_valid, syntax_errors = self._validate_syntax(normalized_query)
        errors.extend(syntax_errors)
        
        # 2. Operation validation
        operation_valid, operation_errors, blocked_ops = self._validate_operations(normalized_query)
        errors.extend(operation_errors)
        blocked_operations.extend(blocked_ops)
        
        # 3. Table and column validation
        table_valid, table_errors, allowed_tables = self._validate_tables_and_columns(normalized_query)
        errors.extend(table_errors)
        
        # 4. Injection attack detection
        injection_threats = self._detect_injection_attacks(sql_query)
        threats.extend(injection_threats)
        
        # 5. Performance risk assessment
        perf_warnings = self._assess_performance_risks(normalized_query)
        warnings.extend(perf_warnings)
        
        # 6. Information disclosure risks
        disclosure_warnings = self._assess_disclosure_risks(normalized_query)
        warnings.extend(disclosure_warnings)
        
        # 7. Query complexity validation
        complexity_warnings = self._validate_complexity(normalized_query)
        warnings.extend(complexity_warnings)
        
        # Convert high-severity threats to errors
        for threat in threats:
            if threat.severity in ['high', 'critical']:
                errors.append(f"{threat.threat_type}: {threat.description}")
            else:
                warnings.append(f"{threat.threat_type}: {threat.description}")
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(threats, errors, warnings)
        
        # Determine overall validity
        is_valid = (
            syntax_valid and 
            operation_valid and 
            table_valid and
            len(errors) == 0 and
            safety_score >= 0.7
        )
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            safety_score=safety_score,
            blocked_operations=blocked_operations,
            allowed_tables=allowed_tables,
            syntax_valid=syntax_valid
        )
    
    def _normalize_query(self, sql_query: str) -> str:
        """Normalize SQL query for analysis."""
        # Remove comments
        sql_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
        sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
        
        # Normalize whitespace
        sql_query = re.sub(r'\s+', ' ', sql_query.strip())
        
        return sql_query
    
    def _validate_syntax(self, query: str) -> Tuple[bool, List[str]]:
        """Basic syntax validation."""
        errors = []
        
        # Check query length
        if len(query) > config.safety.max_query_length:
            errors.append(f"Query too long ({len(query)} > {config.safety.max_query_length} chars)")
        
        # Check for balanced parentheses
        paren_count = query.count('(') - query.count(')')
        if paren_count != 0:
            errors.append("Unbalanced parentheses in query")
        
        # Check for balanced quotes
        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            errors.append("Unbalanced single quotes in query")
        
        double_quotes = query.count('"')
        if double_quotes % 2 != 0:
            errors.append("Unbalanced double quotes in query")
        
        # Basic SQL structure validation
        query_upper = query.upper()
        if not any(query_upper.startswith(op) for op in ['SELECT', 'WITH']):
            errors.append("Query must start with SELECT or WITH")
        
        return len(errors) == 0, errors
    
    def _validate_operations(self, query: str) -> Tuple[bool, List[str], List[str]]:
        """Validate that only allowed operations are used."""
        errors = []
        blocked_ops = []
        
        query_upper = query.upper()
        
        # Check for blocked keywords
        words = re.findall(r'\b[A-Z_]+\b', query_upper)
        
        for word in words:
            if word in self.blocked_keywords:
                blocked_ops.append(word)
                errors.append(f"Blocked operation detected: {word}")
        
        # Check for specific dangerous patterns
        dangerous_patterns = [
            (r'\bEXEC\b|\bEXECUTE\b', "Dynamic SQL execution"),
            (r'\bxp_\w+', "Extended stored procedures"),
            (r'\bsp_\w+', "System stored procedures"),
            (r'\bINTO\s+OUTFILE\b', "File writing operations"),
            (r'\bLOAD_FILE\b', "File reading operations"),
            (r'\bBULK\s+INSERT\b', "Bulk operations"),
            (r'\bOPENROWSET\b', "Remote data access"),
            (r'\bOPENDATASOURCE\b', "External data source access"),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                blocked_ops.append(description)
                errors.append(f"Dangerous operation: {description}")
        
        return len(errors) == 0, errors, blocked_ops
    
    def _validate_tables_and_columns(self, query: str) -> Tuple[bool, List[str], List[str]]:
        """Validate table and column access."""
        errors = []
        allowed_tables = []
        
        # Extract table names from query
        table_pattern = r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)|\bUPDATE\s+(\w+)|\bINTO\s+(\w+)'
        table_matches = re.findall(table_pattern, query, re.IGNORECASE)
        
        tables_in_query = []
        for match in table_matches:
            for table in match:
                if table:
                    tables_in_query.append(table.lower())
        
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
        
        return len(errors) == 0, errors, allowed_tables
    
    def _detect_injection_attacks(self, query: str) -> List[SecurityThreat]:
        """Detect potential SQL injection attacks."""
        threats = []
        
        # SQL injection patterns
        injection_patterns = [
            # Union-based injections
            (r'\bUNION\b.*\bSELECT\b', "union_injection", "high",
             "Potential UNION-based SQL injection", "Use parameterized queries"),
            
            # Comment-based injections
            (r'--|\#|\/\*', "comment_injection", "medium",
             "SQL comments detected (potential injection vector)", "Avoid inline comments"),
            
            # Boolean-based blind injections
            (r'\b(OR|AND)\s+\d+\s*=\s*\d+', "boolean_injection", "high",
             "Potential boolean-based blind injection", "Use proper WHERE conditions"),
            
            # Time-based injections
            (r'\b(SLEEP|WAITFOR|BENCHMARK)\b', "time_injection", "high",
             "Time-based injection functions detected", "Remove timing functions"),
            
            # Stacked queries
            (r';\s*(?:SELECT|INSERT|UPDATE|DELETE)', "stacked_queries", "critical",
             "Multiple statements detected (stacked queries)", "Use single statements only"),
            
            # Information schema access
            (r'\binformation_schema\b', "schema_injection", "medium",
             "Information schema access detected", "Avoid system schema queries"),
            
            # System function abuse
            (r'\b(USER|DATABASE|VERSION|@@\w+)\b', "system_functions", "medium",
             "System functions detected", "Avoid system information functions"),
        ]
        
        query_upper = query.upper()
        
        for pattern, threat_type, severity, description, suggestion in injection_patterns:
            matches = re.finditer(pattern, query_upper, re.IGNORECASE)
            for match in matches:
                threat = SecurityThreat(
                    threat_type=threat_type,
                    severity=severity,
                    description=description,
                    location=f"Position {match.start()}-{match.end()}",
                    suggestion=suggestion
                )
                threats.append(threat)
        
        return threats
    
    def _assess_performance_risks(self, query: str) -> List[str]:
        """Assess potential performance risks."""
        warnings = []
        query_upper = query.upper()
        
        # Check for performance anti-patterns
        if 'SELECT *' in query_upper:
            warnings.append("SELECT * may impact performance; specify needed columns")
        
        if not re.search(r'\bLIMIT\b|\bTOP\b', query_upper):
            warnings.append("Consider adding LIMIT clause for large result sets")
        
        if re.search(r'\bLIKE\s+[\'"]%.*%[\'"]', query):
            warnings.append("Leading wildcard LIKE patterns can be slow")
        
        if re.search(r'\bNOT\s+IN\b', query_upper):
            warnings.append("NOT IN can be slow; consider LEFT JOIN with NULL check")
        
        # Count subqueries
        subquery_count = len(re.findall(r'\(\s*SELECT\b', query_upper))
        if subquery_count > 3:
            warnings.append(f"High number of subqueries ({subquery_count}) may impact performance")
        
        # Count joins
        join_count = len(re.findall(r'\bJOIN\b', query_upper))
        if join_count > 5:
            warnings.append(f"High number of joins ({join_count}) may impact performance")
        
        return warnings
    
    def _assess_disclosure_risks(self, query: str) -> List[str]:
        """Assess information disclosure risks."""
        warnings = []
        query_lower = query.lower()
        
        # Check for potentially sensitive data patterns
        sensitive_patterns = [
            (r'\bpassword\b', "Password field access detected"),
            (r'\bsecret\b', "Secret field access detected"), 
            (r'\btoken\b', "Token field access detected"),
            (r'\bkey\b', "Key field access detected"),
            (r'\bssn\b|social.security', "SSN field access detected"),
            (r'\bcredit.card\b|\bcc.number\b', "Credit card field access detected"),
        ]
        
        for pattern, warning in sensitive_patterns:
            if re.search(pattern, query_lower):
                warnings.append(warning)
        
        return warnings
    
    def _validate_complexity(self, query: str) -> List[str]:
        """Validate query complexity."""
        warnings = []
        
        # Count various complexity indicators
        complexity_metrics = {
            'subqueries': len(re.findall(r'\(\s*SELECT\b', query.upper())),
            'joins': len(re.findall(r'\bJOIN\b', query.upper())),
            'unions': len(re.findall(r'\bUNION\b', query.upper())),
            'aggregates': len(re.findall(r'\b(COUNT|SUM|AVG|MIN|MAX)\b', query.upper())),
            'conditions': len(re.findall(r'\b(WHERE|HAVING)\b', query.upper())),
        }
        
        # Complexity thresholds
        thresholds = {
            'subqueries': 5,
            'joins': 7,
            'unions': 3,
            'aggregates': 10,
            'conditions': 8,
        }
        
        for metric, count in complexity_metrics.items():
            if count > thresholds[metric]:
                warnings.append(f"High {metric} count ({count}) may indicate overly complex query")
        
        return warnings
    
    def _calculate_safety_score(self, threats: List[SecurityThreat], 
                              errors: List[str], warnings: List[str]) -> float:
        """Calculate overall safety score (0.0 to 1.0)."""
        if errors:
            return 0.0
        
        score = 1.0
        
        # Deduct points for threats based on severity
        for threat in threats:
            if threat.severity == 'critical':
                score -= 0.5
            elif threat.severity == 'high':
                score -= 0.3
            elif threat.severity == 'medium':
                score -= 0.2
            elif threat.severity == 'low':
                score -= 0.1
        
        # Deduct smaller amounts for warnings
        score -= len(warnings) * 0.05
        
        return max(0.0, score)
    
    def get_safety_guidelines(self) -> str:
        """Get safety guidelines for SQL query writing."""
        return """
## SQL Safety Guidelines

### Allowed Operations:
- SELECT statements with proper WHERE clauses
- JOIN operations between related tables
- Aggregate functions (COUNT, SUM, AVG, etc.)
- ORDER BY and GROUP BY clauses
- LIMIT clauses (recommended)

### Security Best Practices:
- Always use specific column names instead of SELECT *
- Include LIMIT clauses to prevent large result sets
- Avoid LIKE patterns with leading wildcards
- Use proper JOIN syntax instead of WHERE-based joins
- Avoid accessing system tables or sensitive columns

### Blocked Operations:
- Data modification (INSERT, UPDATE, DELETE)
- Schema changes (CREATE, ALTER, DROP)
- System functions and stored procedures
- File operations and external data access
- Dynamic SQL execution

### Performance Tips:
- Specify needed columns explicitly
- Use appropriate WHERE conditions
- Consider adding LIMIT for exploration queries
- Avoid complex nested subqueries when possible
"""


# Create global safety validator instance
safety_validator = SafetyValidator()