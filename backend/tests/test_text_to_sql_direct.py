#!/usr/bin/env python3
"""
Direct Text-to-SQL agent tests.
Tests SQL generation and execution capabilities without going through manager.
"""
import asyncio
from test_utils import (
    setup_test_environment, 
    get_results_dir, 
    save_test_response,
    print_test_header, 
    print_test_result
)

# Setup environment and imports
setup_test_environment()

from langchain_core.messages import HumanMessage
from text_to_sql.agent.graph import text_to_sql_graph
from text_to_sql.create_sample_data import create_infrastructure_database
from text_to_sql.config import config


def setup_test_environment_sql():
    """Set up test environment with sample database."""
    print("🔧 Setting up test environment...")
    
    # Create infrastructure database
    db_path = create_infrastructure_database()
    print(f"✅ Infrastructure database created at: {db_path}")
    
    return db_path


async def test_infrastructure_queries():
    """Test infrastructure-related queries."""
    
    test_queries = [
        {
            "name": "Load Balancer Status Check",
            "query": "Show me all load balancers and their current status"
        },
        {
            "name": "VIP Health Summary", 
            "query": "Which VIPs have unhealthy backend servers?"
        },
        {
            "name": "Data Center Capacity",
            "query": "What's the total power usage across all data centers?"
        },
        {
            "name": "WIP Performance",
            "query": "Show me WIP performance for www.company.com"
        },
        {
            "name": "SSL Certificate Expiry",
            "query": "Which SSL certificates are expiring soon?"
        },
        {
            "name": "Geographic Distribution",
            "query": "How are our services distributed across regions?"
        }
    ]
    
    print_test_header("Text-to-SQL Infrastructure Queries", f"Testing {len(test_queries)} SQL scenarios")
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print("-" * 40)
        
        try:
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=test_case['query'])],
                "original_query": test_case['query'],
                "natural_language_query": test_case['query'],
                "include_reasoning": True,
                "validation_errors": []
            }
            
            # Run the agent
            result = await text_to_sql_graph.ainvoke(initial_state)
            
            # Display results
            if result.get("execution_error") is None:
                print_test_result(True)
                
                # Save response using utility function
                content = (
                    f"Test: {test_case['name']}\n"
                    f"Query: {test_case['query']}\n"
                    f"Full Response:\n{result.get('formatted_response', 'No response')}\n"
                )
                
                response_file = save_test_response("text_to_sql", i, test_case['name'], content)
                print(f"📁 Full response written to {response_file.name}")
            else:
                error_msg = result.get('execution_error', 'Unknown error')
                print_test_result(False, error_msg)
                
        except Exception as e:
            print_test_result(False, f"Exception: {str(e)}")


async def run_tests():
    """Run all tests."""
    print_test_header("Starting Text-to-SQL Agent Tests")
    
    # Setup
    setup_test_environment_sql()
    
    # Run infrastructure tests
    await test_infrastructure_queries()
    
    print("\n✅ Tests completed!")


if __name__ == "__main__":
    asyncio.run(run_tests())