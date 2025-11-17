"""
Validator node for Text-to-SQL pipeline.

Validates generated SQL queries for safety and security, including:
- Blocking destructive operations (DELETE, DROP, UPDATE, etc.)
- Enforcing read-only access patterns
- Checking table access permissions
- Validating against business rules

Note: Syntax validation is handled by the database during execution.
"""
from typing import Dict, Any
import logging

from ...tools.safety_validator import safety_validator
from ..state import TextToSQLState

logger = logging.getLogger(__name__)


def validator(state: TextToSQLState) -> Dict[str, Any]:
    """
    Validate the generated SQL query for safety and security.

    Focuses on business rules, security, and safety - syntax validation
    is handled by the database during execution.
    """
    generated_sql = state["generated_sql"]
    
    logger.info(f"Validating SQL query: {generated_sql[:100]}...")
    
    # Perform comprehensive validation using safety validator
    validation_result = safety_validator.validate_query(generated_sql)
    
    # Create safety checks summary
    safety_checks = {
        "no_critical_errors": len(validation_result["errors"]) == 0,
        "safe_tables_only": len(validation_result["allowed_tables"]) > 0,
        "is_valid": validation_result["is_valid"]
    }
    
    # Log validation results
    if validation_result["is_valid"]:
        logger.info("SQL validation passed all safety checks")
    else:
        logger.warning(f"SQL validation failed: {validation_result['errors']}")
    
    # Log the reasoning step
    if validation_result["errors"]:
        details = f"Validation found {len(validation_result['errors'])} issues. First issue: {validation_result['errors'][0]}"
        status = "⚠️"
    else:
        details = "The generated SQL passed all safety and security checks."
        status = "✅"
    
    reasoning_step = {
        "step_name": "Validation",
        "details": details,
        "status": status
    }

    # Set validation_error if there are issues
    validation_error = None
    if validation_result["errors"]:
        validation_error = validation_result["errors"][0]  # Use first error as the main error
    
    return {
        "is_valid": validation_result["is_valid"],
        "validation_results": validation_result,
        "safety_checks": safety_checks,
        "validation_error": validation_error,
        "reasoning_log": [reasoning_step]
    }


