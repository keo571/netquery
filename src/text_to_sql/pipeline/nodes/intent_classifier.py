"""
Intent classifier node - classifies user query intent and extracts query.

This node:
1. Extracts the current query from conversation context
2. Classifies intent (sql/general/mixed) using LLM with JSON output
3. For general questions: Returns direct answer immediately
4. For SQL/mixed queries: Passes to cache lookup for further processing

Performance Impact:
- ~200ms for LLM-based intent classification
- General intent: Skip entire SQL pipeline (answer provided directly)
- SQL/mixed intent: Continue to cache lookup
"""
import logging
import time
from typing import Dict, Any
from ..state import TextToSQLState, create_success_step
from ...utils.query_extraction import extract_current_query
from ...utils.query_rewriter import classify_intent

logger = logging.getLogger(__name__)


def intent_classifier_node(state: TextToSQLState) -> Dict[str, Any]:
    """
    Classify query intent and extract current query.

    Flow:
    1. Extract query from conversation context
    2. Get schema summary for domain-aware classification
    3. Classify intent (sql/general/mixed) using LLM with schema context
    4. Route based on intent:
       - general → Return direct answer (skip SQL pipeline)
       - sql/mixed → Continue to cache lookup

    Returns:
        State updates with intent classification results
    """
    start_time = time.time()

    # ================================================================
    # Step 1: Extract query from conversation context
    # ================================================================
    full_query = state["original_query"]
    extracted_query = extract_current_query(full_query)

    logger.debug(f"Extracted query: '{extracted_query[:50]}...'")

    # ================================================================
    # Step 2: Get cached schema summary for domain-aware classification
    # ================================================================
    from src.api.app_context import AppContext
    schema_summary = ""
    try:
        app_context = AppContext.get_instance()
        # Use pre-built cached string (built once at startup, zero overhead)
        schema_summary = app_context.get_schema_summary_string()
    except Exception as e:
        logger.warning(f"Could not load schema summary for intent classification: {e}")

    # ================================================================
    # Step 3: Classify intent using LLM (with conversation context + schema)
    # ================================================================
    llm_start = time.time()
    intent_result = classify_intent(
        extracted_query,
        full_query=full_query,
        schema_summary=schema_summary
    )
    intent = intent_result.intent
    llm_time_ms = (time.time() - llm_start) * 1000

    logger.info(f"⏱️  Intent classification took {llm_time_ms:.0f}ms → result: {intent}")

    # ================================================================
    # Step 4: Handle based on intent
    # ================================================================

    # Base state (always include these)
    result = {
        "extracted_query": extracted_query,
        "intent": intent
    }

    if intent == "general":
        # General intent - provide direct answer and skip SQL pipeline
        logger.info(f"🧠 General question detected - answering directly")

        general_answer = intent_result.general_answer or "I can help with that question."

        result.update({
            "general_answer": general_answer,
            "final_response": general_answer,
            "generated_sql": "",  # No SQL for general questions
            "reasoning_log": [create_success_step(
                "Intent Classification",
                "General question detected - provided direct answer without database query."
            )]
        })

    elif intent == "mixed":
        # Mixed intent - store general answer, continue with SQL
        logger.info(f"🔀 Mixed question detected - will provide both answer and SQL results")

        result.update({
            "general_answer": intent_result.general_answer,
            "sql_query": intent_result.sql_query,  # SQL part extracted by LLM
            "reasoning_log": [create_success_step(
                "Intent Classification",
                "Mixed question detected - will provide both general answer and database results."
            )]
        })

    else:  # intent == "sql"
        # Pure SQL intent - continue to cache lookup
        logger.info(f"💾 SQL question detected - continuing to cache lookup")

        result.update({
            "sql_query": intent_result.sql_query,  # May be rewritten by LLM
            "reasoning_log": [create_success_step(
                "Intent Classification",
                "SQL question detected - continuing to cache lookup."
            )]
        })

    return result
