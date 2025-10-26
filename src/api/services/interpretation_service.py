"""
LLM-powered interpretation service for API responses.
Provides intelligent insights for query results.
"""
import json
import logging
from typing import Dict, List, Any, Optional

from src.text_to_sql.utils.llm_utils import get_llm
from .visualization_service import generate_visualization

logger = logging.getLogger(__name__)


async def get_interpretation(
    query: str,
    results: List[Dict],
    total_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get LLM-powered interpretation for API responses.

    Args:
        query: Original natural language query
        results: Query results (list of dicts, max 100 rows from cache)
        total_rows: Total number of rows in the dataset (if known, up to 1000)

    Returns:
        Dictionary with interpretation and visualization suggestions
    """
    try:
        # If no results, return simple message
        if not results:
            return {
                "interpretation": {
                    "summary": "No data found matching your query",
                    "key_findings": []
                },
                "visualization": None
            }

        # Check if data is truncated
        truncated = total_rows is None or (total_rows and total_rows > len(results))

        prompt = create_interpretation_prompt(query, results, total_rows, truncated)

        # Get LLM response
        llm = get_llm()
        response = await llm.ainvoke(prompt)

        # Extract text content from AIMessage
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse interpretation only (no visualization)
        interpretation = parse_interpretation_response(response_text)

        # Generate visualization separately if needed
        visualization = None
        if results:
            visualization = await generate_visualization(query, results)

        return {
            "interpretation": interpretation,
            "visualization": visualization
        }

    except Exception as e:
        logger.error(f"Error in LLM interpretation: {e}")
        return _get_fallback_response()


def create_interpretation_prompt(
    query: str,
    results: List[Dict],
    total_rows: Optional[int],
    truncated: bool
) -> str:
    """
    Create a focused prompt for the LLM to interpret results.
    """
    # Convert results to a readable format
    if results:
        columns = list(results[0].keys())
        results_text = "Columns: " + ", ".join(columns) + "\n\n"
        results_text += f"Data ({len(results)} rows):\n"
        for i, row in enumerate(results, 1):
            results_text += f"Row {i}: {json.dumps(row, default=str)}\n"
    else:
        results_text = "No results returned"

    truncation_note = ""
    if truncated:
        if total_rows is not None:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from total {total_rows} rows."
        else:
            truncation_note = f"\nNote: Analysis based on {len(results)} cached rows from a large dataset (>1000 rows total)."

    prompt = f"""Analyze query results for a network infrastructure system.

Query: "{query}"
Results: {len(results)} rows{truncation_note}

{results_text}

Provide CONCISE analysis in JSON format:
{{
    "summary": "Direct 1-sentence answer to the query",
    "key_findings": [
        "Critical insight 1 (with specific values)",
        "Critical insight 2 (with specific values)",
        "Critical insight 3 (with specific values)"
    ]
}}

Keep findings actionable and specific. Focus on operational impact.
"""

    return prompt


def parse_interpretation_response(llm_response: str) -> Dict[str, Any]:
    """Parse LLM response for interpretation only."""
    try:
        response_text = _extract_json_from_response(llm_response)
        parsed = json.loads(response_text)

        return {
            "summary": parsed.get("summary", "Analysis complete"),
            "key_findings": parsed.get("key_findings", [])
        }

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logger.error(f"JSON parsing failed: {e}")
        logger.error(f"LLM response: {llm_response[:500]}")  # Log first 500 chars
        logger.error(f"Extracted text: {_extract_json_from_response(llm_response)[:500]}")
        return {
            "summary": "Analysis temporarily unavailable. Your data was retrieved successfully.",
            "key_findings": []
        }


def _get_fallback_response() -> Dict[str, Any]:
    """Return standardized fallback response when LLM fails."""
    return {
        "interpretation": {
            "summary": "Analysis temporarily unavailable. Your data was retrieved successfully.",
            "key_findings": []
        },
        "visualization": None
    }


def _extract_json_from_response(response: str) -> str:
    """Extract JSON content from LLM response, removing markdown code blocks if present."""
    response_text = response.strip()

    # Handle markdown code blocks (```json ... ``` or ``` ... ```)
    if "```" in response_text:
        # Find the first opening backticks
        start = response_text.find("```")
        # Skip past the opening backticks and optional language identifier
        start = response_text.find("\n", start) + 1

        # Find the closing backticks
        end = response_text.find("```", start)

        if start > 0 and end > start:
            response_text = response_text[start:end].strip()

    return response_text


