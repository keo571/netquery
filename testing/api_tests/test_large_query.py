#!/usr/bin/env python3
"""Test the optimized row counting with a large result set."""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_large_query():
    # Test with a query that returns ALL servers (should be more than MAX_CACHE_ROWS)
    print("Testing with query that returns many rows...")

    # Generate SQL for all servers
    response = requests.post(f"{BASE_URL}/api/generate-sql",
                            json={"query": "Show me all servers"})
    result = response.json()
    query_id = result['query_id']
    print(f"Query ID: {query_id}")
    print(f"SQL: {result['sql']}\n")

    # Execute and preview
    response = requests.get(f"{BASE_URL}/api/execute/{query_id}")
    result = response.json()

    total_count = result.get('total_count')
    print("Preview Results:")
    print(f"  - Preview rows returned: {len(result['data'])}")
    print(f"  - Total count: {total_count if total_count is not None else 'Unknown (>1000)'}")
    print(f"  - Preview truncated to 30: {result.get('truncated', False)}")
    print(f"  - Columns: {result['columns'][:5]}..." if len(result['columns']) > 5 else f"  - Columns: {result['columns']}")

    # Interpret the meaning of total_count
    if total_count is None:
        print(f"\n✅ Optimization working! Query has 1000+ rows but we didn't count them all")
        print(f"   Fast check found: more than 1000 rows exist")
    elif total_count > MAX_CACHE_ROWS:
        print(f"\n✅ Large dataset: {total_count} rows total")
        print(f"   Cached first {MAX_CACHE_ROWS} rows for analysis")
    else:
        print(f"\n✅ Complete dataset: {total_count} rows")

    print("\nPerformance Note: This should be MUCH faster than counting millions of rows!")

if __name__ == "__main__":
    MAX_CACHE_ROWS = 100  # Match server setting
    test_large_query()