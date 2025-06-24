"""
Validator node for Text-to-SQL agent.
Validates generated SQL queries for safety, syntax, and correctness.
"""
from typing import Dict, Any
import logging

from ...tools.safety_validator import safety_validator
from ...config import config
from ..state import TextToSQLState

logger = logging.getLogger(__name__)


def validator_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Validate the generated SQL query for safety, syntax, and correctness.
    
    This node:
    1. Performs comprehensive safety validation
    2. Checks syntax and structure
    3. Validates against schema constraints
    4. Provides detailed validation results
    """
    try:
        generated_sql = state.get("generated_sql", "")
        relevant_tables = state.get("relevant_tables", [])
        
        if not generated_sql:
            return {
                "is_valid": False,
                "validation_results": {
                    "is_valid": False,
                    "errors": ["No SQL query provided for validation"],
                    "warnings": [],
                    "safety_score": 0.0,
                    "blocked_operations": [],
                    "allowed_tables": [],
                    "syntax_valid": False
                },
                "safety_checks": {"basic_check": False},
                "validation_errors": ["No SQL query to validate"]
            }
        
        logger.info(f"Validating SQL query: {generated_sql[:100]}...")
        
        # Perform comprehensive validation using safety validator
        validation_result = safety_validator.validate_query(generated_sql)
        
        # Additional custom validations
        additional_checks = _perform_additional_validations(generated_sql, relevant_tables)
        
        # Combine validation results
        combined_errors = list(validation_result["errors"])
        combined_warnings = list(validation_result["warnings"])
        
        combined_errors.extend(additional_checks.get("errors", []))
        combined_warnings.extend(additional_checks.get("warnings", []))
        
        # Update validation result
        validation_result["errors"] = combined_errors
        validation_result["warnings"] = combined_warnings
        validation_result["is_valid"] = (
            validation_result["syntax_valid"] and
            len(combined_errors) == 0 and
            validation_result["safety_score"] >= 0.7
        )
        
        # Create safety checks summary
        safety_checks = {
            "syntax_valid": validation_result["syntax_valid"],
            "no_blocked_operations": len(validation_result["blocked_operations"]) == 0,
            "safe_tables_only": len(validation_result["allowed_tables"]) > 0,
            "high_safety_score": validation_result["safety_score"] >= 0.7,
            "no_critical_errors": len(combined_errors) == 0
        }
        
        # Log validation results
        if validation_result["is_valid"]:
            logger.info(f"SQL validation passed with safety score {validation_result['safety_score']:.2f}")
        else:
            logger.warning(f"SQL validation failed: {combined_errors}")
        
        # Log the reasoning step
        if combined_errors:
            details = f"Validation found {len(combined_errors)} issues. First issue: {combined_errors[0]}"
            status = "⚠️"
        else:
            details = "The generated SQL passed all safety and syntax checks."
            status = "✅"
        
        reasoning_step = {
            "step_name": "Validation",
            "details": details,
            "status": status
        }

        return {
            "is_valid": validation_result["is_valid"],
            "validation_results": validation_result,
            "safety_checks": safety_checks,
            "validation_errors": combined_errors if combined_errors else [],
            "reasoning_log": [reasoning_step]
        }
        
    except Exception as e:
        logger.error(f"SQL validation failed: {str(e)}")
        return {
            "is_valid": False,
            "validation_results": {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "safety_score": 0.0,
                "blocked_operations": [],
                "allowed_tables": [],
                "syntax_valid": False
            },
            "safety_checks": {"validation_error": True},
            "validation_errors": [f"Validation error: {str(e)}"],
            "reasoning_log": []
        }


def _perform_additional_validations(sql_query: str, relevant_tables: list) -> Dict[str, Any]:
    """Perform additional custom validations beyond the safety validator."""
    errors = []
    warnings = []
    
    sql_upper = sql_query.upper()
    
    # 1. Check if query uses only relevant tables
    if relevant_tables:
        for table in relevant_tables:
            if table.upper() not in sql_upper:
                warnings.append(f"Relevant table '{table}' not used in query")
    
    # 2. Check for reasonable LIMIT clause
    if 'LIMIT' in sql_upper:
        import re
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_query, re.IGNORECASE)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > config.safety.max_result_rows:
                errors.append(f"LIMIT value {limit_value} exceeds maximum allowed {config.safety.max_result_rows}")
            elif limit_value <= 0:
                errors.append(f"LIMIT value must be positive, got {limit_value}")
    else:
        # Warn about missing LIMIT for potentially large result sets
        if 'GROUP BY' not in sql_upper and 'COUNT(' not in sql_upper:
            warnings.append("Consider adding LIMIT clause to prevent large result sets")
    
    # 3. Check for proper JOIN syntax
    if ',' in sql_query and 'FROM' in sql_upper:
        # Check if using old-style comma joins
        from_clause_match = re.search(r'FROM\s+(.*?)(?:\s+WHERE|\s+GROUP|\s+ORDER|\s+LIMIT|$)', 
                                     sql_query, re.IGNORECASE | re.DOTALL)
        if from_clause_match:
            from_clause = from_clause_match.group(1)
            if ',' in from_clause and 'JOIN' not in from_clause.upper():
                warnings.append("Consider using explicit JOIN syntax instead of comma-separated tables")
    
    # 4. Check for potential performance issues
    if re.search(r"LIKE\s+['\"]%.*%['\"]", sql_query, re.IGNORECASE):
        warnings.append("LIKE pattern with leading and trailing wildcards may be slow")
    
    # 5. Check for proper string comparison
    if "LIKE" in sql_upper and "UPPER(" not in sql_upper and "LOWER(" not in sql_upper:
        warnings.append("Consider using UPPER() or LOWER() for case-insensitive string matching")
    
    # 6. Validate parentheses balance
    if sql_query.count('(') != sql_query.count(')'):
        errors.append("Unbalanced parentheses in SQL query")
    
    # 7. Check for proper quote usage
    single_quote_count = sql_query.count("'")
    if single_quote_count % 2 != 0:
        errors.append("Unbalanced single quotes in SQL query")
    
    # 8. Check for SQL injection patterns (additional to safety validator)
    suspicious_patterns = [
        r';\s*DROP\s+TABLE',
        r';\s*DELETE\s+FROM',
        r';\s*UPDATE\s+.*SET',
        r'UNION\s+ALL\s+SELECT.*FROM\s+information_schema'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, sql_query, re.IGNORECASE):
            errors.append(f"Suspicious SQL pattern detected: potential injection attempt")
            break
    
    return {
        "errors": errors,
        "warnings": warnings
    }