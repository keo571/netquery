#!/usr/bin/env python3
"""Test script for FastAPI endpoints."""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    # 1. Generate SQL
    print("1. Testing /api/generate-sql")
    response = requests.post(f"{BASE_URL}/api/generate-sql",
                            json={"query": "Show all servers with high memory usage"})
    result = response.json()
    print(f"   Query ID: {result['query_id']}")
    print(f"   SQL: {result['sql']}")
    query_id = result['query_id']

    # 2. Execute and preview results
    print("\n2. Testing /api/execute/{query_id}")
    response = requests.get(f"{BASE_URL}/api/execute/{query_id}")
    result = response.json()
    total_count = result.get('total_count')
    print(f"   Total rows: {total_count if total_count is not None else 'Unknown (>1000)'}")
    print(f"   Preview rows: {len(result.get('data', []))}")
    print(f"   Preview truncated: {result.get('truncated', False)}")
    print(f"   Columns: {result.get('columns', [])}")
    if result.get('data'):
        print(f"   First row: {result['data'][0]}")

    # 3. Interpret results
    print("\n3. Testing /api/interpret/{query_id}")
    response = requests.post(f"{BASE_URL}/api/interpret/{query_id}")
    result = response.json()
    print(f"   Summary: {result.get('interpretation', {}).get('summary', 'N/A')}")
    print(f"   Findings: {len(result.get('interpretation', {}).get('key_findings', []))} findings")
    viz = result.get('visualization')
    print(f"   Visualization: {viz['type'] if viz else 'None'} suggested")

    # 4. Test health check
    print("\n4. Testing /health")
    response = requests.get(f"{BASE_URL}/health")
    result = response.json()
    print(f"   Status: {result['status']}")
    print(f"   Cache size: {result['cache_size']}")

if __name__ == "__main__":
    test_api()