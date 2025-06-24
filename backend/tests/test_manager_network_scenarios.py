#!/usr/bin/env python3
"""
Network Infrastructure Manager Agent Routing Test.
Tests routing for network engineering queries with real LLM-generated RAG responses.
"""
import asyncio
import os
from datetime import datetime
from test_utils import (
    setup_test_environment,
    get_results_dir,
    get_log_file,
    save_test_response,
    print_test_header,
    print_test_result
)

# Setup environment and imports
setup_test_environment()

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from manager.graph import graph


def create_network_test_cases():
    """Create network infrastructure-focused test cases for routing."""
    return [
        # Infrastructure Database Queries (should route to text_to_sql)
        {
            "name": "Load Balancer Health Check",
            "query": "Show me all load balancers with unhealthy backend servers",
            "expected_agent": "text_to_sql",
            "type": "infrastructure_monitoring",
            "context": "Real-time infrastructure status from monitoring database"
        },
        {
            "name": "VIP Status Query",
            "query": "Which VIPs are currently down or experiencing issues?",
            "expected_agent": "text_to_sql", 
            "type": "network_status",
            "context": "Current network status from infrastructure database"
        },
        {
            "name": "Data Center Power Usage",
            "query": "What's the total power consumption across all data centers?",
            "expected_agent": "text_to_sql",
            "type": "capacity_management",
            "context": "Power metrics from infrastructure monitoring"
        },
        {
            "name": "SSL Certificate Expiry",
            "query": "Which SSL certificates are expiring in the next 30 days?",
            "expected_agent": "text_to_sql",
            "type": "certificate_management",
            "context": "Certificate inventory from security database"
        },
        
        # Network Engineering Documentation Queries (should route to RAG)
        {
            "name": "Load Balancer Configuration",
            "query": "How do I configure a new F5 load balancer for high availability?",
            "expected_agent": "rag",
            "type": "configuration_procedures",
            "context": "Network configuration documentation and runbooks"
        },
        {
            "name": "Network Troubleshooting",
            "query": "What's the standard procedure for troubleshooting BGP routing issues?",
            "expected_agent": "rag",
            "type": "troubleshooting_guides",
            "context": "Network troubleshooting documentation"
        },
        {
            "name": "Security Policy",
            "query": "What are our firewall rules for DMZ to internal network communication?",
            "expected_agent": "rag",
            "type": "security_policies",
            "context": "Network security policies and procedures"
        },
        {
            "name": "Change Management",
            "query": "What's the process for implementing network changes in production?",
            "expected_agent": "rag",
            "type": "operational_procedures",
            "context": "Change management and operational procedures"
        },
        {
            "name": "Incident Response",
            "query": "How do we handle a complete data center outage?",
            "expected_agent": "rag",
            "type": "incident_procedures",
            "context": "Disaster recovery and incident response playbooks"
        },
        
        # Mixed Queries (requiring both agents)
        {
            "name": "Performance + Procedures",
            "query": "Show me current WIP performance issues and the escalation procedure for critical alerts",
            "expected_agent": "multiple",
            "type": "mixed_analysis",
            "context": "Both real-time data and procedural documentation"
        }
    ]


async def simulate_network_rag_response_with_llm(query: str, query_type: str) -> dict:
    """Generate realistic RAG responses using LLM for network engineering queries."""
    
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.2,
        max_retries=2,
        api_key=os.getenv("GEMINI_API_KEY"),
    )
    
    # Since there's NO knowledge base/vector store, all queries have the same status
    knowledge_status = "no_knowledge_base"
    
    # Create prompt that simulates RAG agent without any knowledge base
    rag_simulation_prompt = f"""You are a Network Engineering RAG (Retrieval-Augmented Generation) agent. A network engineer has asked you: "{query}"

**Your Current Situation:** You have NO knowledge base or vector store available. No company documents, no configuration templates, no internal procedures - nothing.

**Instructions:**
1. Clearly state that you don't have any knowledge base or company documentation
2. Provide helpful general network engineering guidance based only on your training data
3. Explain what type of documentation would be needed to give a complete answer
4. Suggest where they might find this information
5. Be honest that you're only providing general industry knowledge

**Response Format:**
- Start by clearly stating you have no knowledge base
- Provide general industry best practices and principles  
- Explain what specific company documentation would be needed
- Suggest practical next steps and resources
- Keep tone professional and helpful for network engineers

**Important:** Don't pretend to have access to any company-specific information. Make it clear this is general guidance only."""

    try:
        # Generate response using LLM
        response = await llm.ainvoke(rag_simulation_prompt)
        answer = response.content
        
        # Since there's no knowledge base, confidence should be moderate
        confidence = 0.60
        
        return {
            "agent_id": "rag",
            "session_id": f"rag_network_session",
            "success": True,
            "answer": answer,
            "confidence": confidence,
            "reasoning_steps": [
                {"step": 1, "action": "knowledge_base_search", "result": "No knowledge base available"},
                {"step": 2, "action": "fallback_to_training", "result": "Using general network engineering knowledge only"},
                {"step": 3, "action": "response_generation", "result": "Generated response with clear limitations noted"}
            ],
            "sources": [
                {"type": "training_data", "source": "general_network_engineering_knowledge", "relevance": 0.8},
                {"type": "knowledge_base", "source": "none_available", "relevance": 0.0}
            ],
            "execution_time": 2.1,
            "error_message": None,
            "knowledge_base_status": knowledge_status,
            "llm_generated": True,
            "has_vector_store": False
        }
        
    except Exception as e:
        return {
            "agent_id": "rag",
            "session_id": f"rag_network_session_error",
            "success": False,
            "answer": f"Error generating RAG response: {str(e)}",
            "confidence": 0.0,
            "reasoning_steps": [
                {"step": 1, "action": "llm_call", "result": f"Failed: {str(e)}"}
            ],
            "sources": [],
            "execution_time": 0.0,
            "error_message": str(e),
            "knowledge_base_status": "error",
            "llm_generated": False,
            "has_vector_store": False
        }


async def test_network_routing():
    """Test network-focused manager agent routing with real LLM responses."""
    print_test_header("Network Infrastructure Manager Routing", "Testing with real LLM responses")
    
    test_cases = create_network_test_cases()
    routing_results = {
        "text_to_sql": 0,
        "rag": 0,
        "multiple": 0,
        "manager": 0,
        "unknown": 0
    }
    
    # Setup logging
    log_file = get_log_file("manager_network_routing")
    results_dir = get_results_dir("manager_network_routing")
    
    print(f"📋 Testing {len(test_cases)} network engineering scenarios...")
    print(f"📁 Results: {results_dir}")
    print(f"📄 Log: {log_file}")
    
    with open(log_file, "w") as log:
        log.write(f"Manager Network Routing Test - {datetime.now()}\n")
        log.write("=" * 50 + "\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔧 Test {i}: {test_case['name']}")
            print(f"Query: {test_case['query']}")
            print(f"Expected Route: {test_case['expected_agent']}")
            print(f"Context: {test_case['context']}")
            print("-" * 50)
            
            # Log test details
            log.write(f"\nTest {i}: {test_case['name']}\n")
            log.write(f"Query: {test_case['query']}\n")
            log.write(f"Expected: {test_case['expected_agent']}\n")
            
            try:
                # Invoke manager agent
                result = await graph.ainvoke({
                    "messages": [HumanMessage(content=test_case['query'])]
                })
                
                # Extract routing information
                classification = result.get('query_classification', 'unknown')
                active_agents = result.get('active_agents', [])
                confidence = result.get('confidence_score', 0.0)
                
                # Determine actual routing
                if active_agents:
                    actual_agent = active_agents[0] if len(active_agents) == 1 else "multiple"
                else:
                    actual_agent = "manager"
                
                print(f"🎯 Classification: {classification}")
                print(f"📊 Confidence: {confidence:.2f}")
                print(f"🤖 Routed to: {actual_agent}")
                
                # Log results
                log.write(f"Actual: {actual_agent}\n")
                log.write(f"Classification: {classification}\n")
                log.write(f"Confidence: {confidence:.2f}\n")
                
                # Routing accuracy check
                expected = test_case['expected_agent']
                if actual_agent == expected:
                    print_test_result(True, "Routing correct")
                    log.write("Result: CORRECT\n")
                else:
                    print_test_result(False, f"Expected {expected}, got {actual_agent}")
                    log.write(f"Result: MISMATCH\n")
                
                routing_results[actual_agent] += 1
                
                # Generate real LLM response for RAG queries
                if 'rag' in str(active_agents):
                    print(f"\n📚 Generating Real RAG Response with LLM...")
                    rag_response = await simulate_network_rag_response_with_llm(
                        test_case['query'], 
                        test_case['type']
                    )
                    
                    if rag_response['success']:
                        print(f"   🔍 Knowledge Status: {rag_response['knowledge_base_status']}")
                        print(f"   📈 Confidence: {rag_response['confidence']:.2f}")
                        print(f"   🤖 LLM Generated: {rag_response['llm_generated']}")
                        print(f"   📝 Response Length: {len(rag_response['answer'])} characters")
                        
                        # Show preview
                        print(f"\n   💬 LLM Response Preview:")
                        print(f"   {rag_response['answer'][:200]}...")
                        
                        # Save full response using utility
                        content = (
                            f"Test: {test_case['name']}\n"
                            f"Query: {test_case['query']}\n"
                            f"Type: {test_case['type']}\n"
                            f"Knowledge Status: {rag_response['knowledge_base_status']}\n"
                            f"Confidence: {rag_response['confidence']:.2f}\n"
                            f"Timestamp: {datetime.now()}\n"
                            f"{'-' * 50}\n\n"
                            f"Full LLM Response:\n{rag_response['answer']}\n"
                        )
                        
                        response_file = save_test_response("manager_network_routing", i, f"rag_{test_case['name']}", content)
                        print(f"   📁 Saved to {response_file.name}")
                        log.write(f"RAG Response saved to: {response_file.name}\n")
                    else:
                        print_test_result(False, f"RAG Error: {rag_response['error_message']}")
                        log.write(f"RAG Error: {rag_response['error_message']}\n")
                
                # Show manager response preview
                response = result.get('final_answer', 'No response')
                print(f"\n📝 Manager Response Preview: {response[:120]}...")
                
            except Exception as e:
                print_test_result(False, str(e))
                log.write(f"Error: {str(e)}\n")
                routing_results["unknown"] += 1
                
            print("-" * 50)
            log.write("-" * 30 + "\n")
    
    # Display routing statistics
    print(f"\n📊 Network Engineering Query Routing Results:")
    print("=" * 50)
    total_tests = len(test_cases)
    
    for agent, count in routing_results.items():
        if count > 0:
            percentage = (count / total_tests) * 100
            print(f"📍 {agent:15}: {count:2d} queries ({percentage:5.1f}%)")
    
    # Save summary using utility
    summary_content = (
        f"Manager Agent Routing Test Summary\n"
        f"{'=' * 50}\n\n"
        f"Total tests: {total_tests}\n\n"
        f"Routing Results:\n"
    )
    for agent, count in routing_results.items():
        if count > 0:
            percentage = (count / total_tests) * 100
            summary_content += f"  {agent}: {count} queries ({percentage:.1f}%)\n"
    
    summary_file = save_test_response("manager_network_routing", 0, "test_summary", summary_content)
    print(f"\n📁 Test summary saved to: {summary_file}")
    
    return routing_results


if __name__ == "__main__":
    print_test_header("Starting Network Infrastructure Manager Routing Tests with Real LLM")
    
    async def run_network_tests():
        routing_stats = await test_network_routing()
        
        print(f"\n✅ Network routing tests completed!")
        print(f"📈 Final Results: {routing_stats}")
        
        # Summary recommendations
        rag_queries = routing_stats.get('rag', 0)
        if rag_queries > 0:
            print(f"\n💡 RAG Integration Notes:")
            print(f"   📚 {rag_queries} queries generated real LLM responses")
            print(f"   🔍 Review responses to understand LLM behavior without knowledge base")
    
    asyncio.run(run_network_tests())