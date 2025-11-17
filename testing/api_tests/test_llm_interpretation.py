#!/usr/bin/env python3
"""Test the new LLM-powered interpretation service."""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_llm_interpretation():
    print("Testing LLM-Powered Interpretation Service\n")
    print("=" * 60)

    # Step 1: Generate SQL for a meaningful query
    print("\n1. Generating SQL for: 'Show me servers with high CPU usage'")
    response = requests.post(f"{BASE_URL}/api/generate-sql",
                            json={"query": "Show me servers with high CPU usage"})
    result = response.json()
    query_id = result['query_id']
    print(f"   ✓ Query ID: {query_id}")
    print(f"   ✓ SQL: {result['sql'][:80]}...")

    # Step 2: Execute and preview
    print("\n2. Executing query and caching results...")
    response = requests.get(f"{BASE_URL}/api/execute/{query_id}")
    result = response.json()
    total_count = result.get('total_count')
    print(f"   ✓ Retrieved {len(result['data'])} preview rows")
    print(f"   ✓ Total count: {total_count if total_count is not None else 'Unknown (>1000)'}")

    # Step 3: Get LLM interpretation
    print("\n3. Getting LLM-powered interpretation...")
    response = requests.post(f"{BASE_URL}/api/interpret/{query_id}")

    if response.status_code == 200:
        result = response.json()

        print("\n" + "=" * 60)
        print("INTERPRETATION RESULTS")
        print("=" * 60)

        # Show interpretation
        interpretation = result.get('interpretation', {})
        print(f"\n📊 Summary:")
        print(f"   {interpretation.get('summary', 'No summary')}")

        print(f"\n🔍 Key Findings:")
        for i, finding in enumerate(interpretation.get('key_findings', []), 1):
            print(f"   {i}. {finding}")


        # Show visualization suggestion
        visualization = result.get('visualization')
        if visualization:
            print(f"\n📈 Suggested Visualization:")
            print(f"   {visualization['type'].upper()} Chart: {visualization['title']}")
            config = visualization.get('config', {})
            if config.get('reason'):
                print(f"      Reason: {config['reason']}")
            print(f"      X: {config.get('x_column')}, Y: {config.get('y_column')}")
        else:
            print(f"\n📈 No visualization suggested")

        print(f"\n✅ Data truncated for interpretation: {result.get('data_truncated', False)}")

    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"   {response.json()}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("\n💡 The interpretation is now powered by LLM instead of basic pandas stats!")
    print("   - Provides intelligent insights based on the query context")
    print("   - Suggests relevant visualizations")
    print("   - Understands the meaning behind the data")
    print("   - Optimized to analyze up to MAX_CACHE_ROWS rows for efficient token usage and faster responses")

if __name__ == "__main__":
    test_llm_interpretation()