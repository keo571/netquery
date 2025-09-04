#!/usr/bin/env python3
"""
Simple CLI wrapper for the Netquery Text-to-SQL system.
Usage: python gemini_cli.py "your query here"
"""
import asyncio
import sys
import os
from dotenv import load_dotenv
from src.text_to_sql.pipeline.graph import text_to_sql_graph

# Load environment variables from .env file
load_dotenv()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python gemini_cli.py 'your query here'")
        print("\nExamples:")
        print("  python gemini_cli.py 'Show me all load balancers'")
        print("  python gemini_cli.py 'Which SSL certificates expire soon?'")
        return
    
    query = " ".join(sys.argv[1:])
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        return
    
    print(f"Processing: {query}")
    print("-" * 50)
    
    try:
        result = await text_to_sql_graph.ainvoke({
            "original_query": query,
            "include_reasoning": True
        })
        
        response = result.get("formatted_response") or result.get("final_response", "No response generated")
        print(response)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())