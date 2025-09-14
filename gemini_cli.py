#!/usr/bin/env python3
"""
Simple CLI wrapper for the Netquery Text-to-SQL system.
Usage: python gemini_cli.py "your query here" [--csv] [--explain] [--html]
"""
import asyncio
import sys
import os
import argparse
import time
from dotenv import load_dotenv
from src.text_to_sql.pipeline.graph import text_to_sql_graph
from src.text_to_sql.utils.html_exporter import create_html_from_cli_output

# Load environment variables from .env file
load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description="Netquery Text-to-SQL CLI")
    parser.add_argument("query", nargs="+", help="Your natural language query")
    parser.add_argument("--csv", action="store_true", help="Save results to CSV")
    parser.add_argument("--explain", action="store_true", help="Show detailed explanations of SQL generation and results")
    parser.add_argument("--html", action="store_true", help="Save results to HTML")
    
    if len(sys.argv) < 2:
        parser.print_help()
        print("\nExamples:")
        print("  python gemini_cli.py 'Show me all load balancers'")
        print("  python gemini_cli.py 'Which SSL certificates expire soon?' --csv")
        print("  python gemini_cli.py 'Show unhealthy servers' --explain")
        print("  python gemini_cli.py 'Show load balancers in us-east-1' --html")
        return
    
    args = parser.parse_args()
    query = " ".join(args.query)
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        return
    
    print(f"Processing: {query}")
    print("-" * 50)
    
    try:
        # Measure total pipeline execution time
        pipeline_start_time = time.time()
        
        result = await text_to_sql_graph.ainvoke({
            "original_query": query,
            "show_explanation": args.explain,
            "export_csv": args.csv,
            "export_html": args.html
        })
        
        pipeline_end_time = time.time()
        total_pipeline_time_ms = (pipeline_end_time - pipeline_start_time) * 1000
        
        # Add total pipeline time to result state for use in formatting
        result["total_pipeline_time_ms"] = total_pipeline_time_ms
        
        response = result.get("formatted_response") or result.get("final_response", "No response generated")
        print(response)
        
        # Add total pipeline timing information with breakdown
        if total_pipeline_time_ms > 0:
            total_seconds = total_pipeline_time_ms / 1000
            print(f"\n⏱️  **Total time:** {total_seconds:.1f}s")
            
            # Show breakdown if available
            schema_time = result.get("schema_analysis_time_ms", 0.0)
            planning_time = result.get("query_planning_time_ms", 0.0) 
            generation_time = result.get("sql_generation_time_ms", 0.0)
            interpretation_time = result.get("interpretation_time_ms", 0.0)
            db_time = result.get("execution_time_ms", 0.0)
            
            if any([schema_time, planning_time, generation_time, interpretation_time]):
                print("   **Breakdown:**")
                if schema_time > 0:
                    print(f"   - Schema analysis: {schema_time/1000:.1f}s")
                if planning_time > 0:
                    print(f"   - Query planning: {planning_time/1000:.1f}s")
                if generation_time > 0:
                    print(f"   - SQL generation: {generation_time/1000:.1f}s")
                if interpretation_time > 0:
                    print(f"   - Result interpretation: {interpretation_time/1000:.1f}s")
                if db_time > 0:
                    print(f"   - Database execution: {db_time/1000:.3f}s")
        
        # Generate HTML if requested
        if args.html:
            try:
                # Build timing breakdown string for HTML
                timing_breakdown = ""
                if total_pipeline_time_ms > 0:
                    schema_time = result.get("schema_analysis_time_ms", 0.0)
                    planning_time = result.get("query_planning_time_ms", 0.0) 
                    generation_time = result.get("sql_generation_time_ms", 0.0)
                    interpretation_time = result.get("interpretation_time_ms", 0.0)
                    db_time = result.get("execution_time_ms", 0.0)
                    
                    timing_breakdown = f"\n\n**⏱️  Total time:** {total_seconds:.1f}s\n\n**Breakdown:**\n"
                    if schema_time > 0:
                        timing_breakdown += f"- Schema analysis: {schema_time/1000:.1f}s\n"
                    if planning_time > 0:
                        timing_breakdown += f"- Query planning: {planning_time/1000:.1f}s\n"
                    if generation_time > 0:
                        timing_breakdown += f"- SQL generation: {generation_time/1000:.1f}s\n"
                    if interpretation_time > 0:
                        timing_breakdown += f"- Result interpretation: {interpretation_time/1000:.1f}s\n"
                    if db_time > 0:
                        timing_breakdown += f"- Database execution: {db_time/1000:.3f}s\n"
                
                html_path = create_html_from_cli_output(
                    query=query,
                    full_output=response + timing_breakdown,
                    chart_html=result.get("chart_html", "")
                )
                print(f"\n🌐 HTML report saved: {html_path}")
            except Exception as html_error:
                print(f"\n⚠️  HTML export failed: {html_error}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())