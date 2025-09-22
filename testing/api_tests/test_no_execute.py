#!/usr/bin/env python3
"""
Test script to verify the execute=False option works correctly.
This tests that the pipeline can generate SQL without executing it.
"""
import asyncio
import os
from dotenv import load_dotenv
from src.text_to_sql.pipeline.graph import text_to_sql_graph

# Load environment variables
load_dotenv()

async def test_no_execute():
    """Test SQL generation without execution."""

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        return

    test_queries = [
        "Show me all load balancers",
        "Which servers are unhealthy?",
        "What's the average memory usage by datacenter?"
    ]

    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing: {query}")
        print('-'*50)

        # Test with execute=False
        print("\n1. Testing with execute=False (SQL generation only):")
        result = await text_to_sql_graph.ainvoke({
            "original_query": query,
            "execute": False,  # Don't execute the SQL
            "show_explanation": False
        })

        print(f"   Generated SQL: {result.get('generated_sql', 'No SQL generated')}")
        print(f"   Query results: {result.get('query_results', 'None (as expected)')}")
        print(f"   Has final response: {'final_response' in result}")

        # Test with execute=True (default behavior)
        print("\n2. Testing with execute=True (full pipeline):")
        result_with_exec = await text_to_sql_graph.ainvoke({
            "original_query": query,
            "execute": True,  # Execute the SQL
            "show_explanation": False
        })

        print(f"   Generated SQL: {result_with_exec.get('generated_sql', 'No SQL generated')}")
        has_results = result_with_exec.get('query_results') is not None
        print(f"   Has query results: {has_results}")
        if has_results:
            print(f"   Number of rows: {len(result_with_exec.get('query_results', []))}")
        print(f"   Has final response: {'final_response' in result_with_exec}")

if __name__ == "__main__":
    asyncio.run(test_no_execute())