#!/usr/bin/env python3
"""
Basic Manager Agent functionality tests.
Tests routing classification and basic agent execution.
"""
import asyncio
from test_utils import setup_test_environment, print_test_header, print_test_result

# Setup environment and imports
setup_test_environment()

from manager.graph import graph
from langchain_core.messages import HumanMessage


async def test_manager_agent():
    """Test the manager agent with different types of queries."""
    
    print_test_header("Manager Agent Basic Tests", "Testing query classification and routing")
    
    # Test cases
    test_cases = [
        {
            "name": "SQL Query",
            "message": "Show me the top 10 customers by revenue this year",
            "expected_classification": "sql"
        },
        {
            "name": "RAG Query", 
            "message": "What does our company policy say about remote work?",
            "expected_classification": "rag"
        },
        {
            "name": "General Query",
            "message": "Hello, how are you?",
            "expected_classification": "general"
        },
        {
            "name": "Mixed Query",
            "message": "Compare our sales data with the market research report about customer preferences",
            "expected_classification": "mixed"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Query: {test_case['message']}")
        print("-" * 30)
        
        try:
            # Invoke the manager agent
            result = await graph.ainvoke({
                "messages": [HumanMessage(content=test_case['message'])]
            })
            
            # Display results
            print(f"🎯 Classification: {result.get('query_classification', 'N/A')}")
            print(f"📊 Confidence: {result.get('confidence_score', 0.0):.2f}")
            print(f"🤖 Active Agents: {result.get('active_agents', [])}")
            print(f"⚡ Execution Mode: {result.get('response_metadata', {}).get('execution_mode', 'N/A')}")
            print(f"📝 Response: {result.get('final_answer', 'No response')[:100]}...")
            
            # Check if classification matches expectation
            expected = test_case['expected_classification']
            actual = result.get('query_classification', 'unknown')
            if actual == expected:
                print_test_result(True, f"Classification correct: {actual}")
            else:
                print_test_result(False, f"Expected {expected}, got {actual}")
                
        except Exception as e:
            print_test_result(False, str(e))
            
        print("-" * 50)


def test_manager_agent_sync():
    """Synchronous wrapper for testing."""
    try:
        print_test_header("Manager Agent Sync Test", "Basic functionality verification")
        
        result = graph.invoke({
            "messages": [HumanMessage(content="Hello, what can you help me with?")]
        })
        
        print(f"📝 Response: {result.get('final_answer', 'No response')[:200]}...")
        print(f"🎯 Classification: {result.get('query_classification', 'N/A')}")
        
        print_test_result(True, "Basic invocation successful")
        return True
        
    except Exception as e:
        print_test_result(False, str(e))
        return False


if __name__ == "__main__":
    print_test_header("Starting Manager Agent Tests")
    
    # Test synchronous version first
    sync_success = test_manager_agent_sync()
    
    if sync_success:
        print("\n🚀 Running async tests...")
        asyncio.run(test_manager_agent())
    else:
        print("❌ Sync test failed, skipping async tests")
    
    print("\n✅ Tests completed!")