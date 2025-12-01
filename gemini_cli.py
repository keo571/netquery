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
from src.common.env import load_environment

# Load environment variables before importing pipeline components
load_environment()

from src.text_to_sql.pipeline.graph import text_to_sql_graph
from src.text_to_sql.utils.html_exporter import create_html_from_cli_output
from src.common.database.engine import cleanup_database_connections

async def main():
    parser = argparse.ArgumentParser(description="Netquery Text-to-SQL CLI")
    parser.add_argument("query", nargs="+", help="Your natural language query")
    parser.add_argument("--csv", action="store_true", help="Save results to CSV")
    parser.add_argument("--explain", action="store_true", help="Show detailed explanations of SQL generation and results")
    parser.add_argument("--html", action="store_true", help="Save results to HTML")
    parser.add_argument("--sql-only", action="store_true", help="Generate SQL only, don't execute it")
    parser.add_argument("--schema", type=str, help="Path to canonical schema JSON file")
    parser.add_argument("--app", type=str, help="Application/schema namespace (e.g., 'app_a', 'app_b'). Used for embedding isolation.")
    parser.add_argument("--database-url", type=str, help="Database URL (overrides DATABASE_URL env var)")
    parser.add_argument("--embedding-database-url", type=str, help="Embedding database URL for pgvector (overrides EMBEDDING_DATABASE_URL env var)")

    if len(sys.argv) < 2:
        parser.print_help()
        print("\nExamples:")
        print("  python gemini_cli.py 'Show me all load balancers'")
        print("  python gemini_cli.py 'Which SSL certificates expire soon?' --csv")
        print("  python gemini_cli.py 'Show unhealthy servers' --explain")
        print("  python gemini_cli.py 'Show load balancers in us-east-1' --html")
        print("  python gemini_cli.py 'Show metrics' --schema schemas/app_a.json --app app_a")
        return

    args = parser.parse_args()
    query = " ".join(args.query)

    # Apply environment defaults for schema inputs when flags are omitted
    if not args.schema:
        env_schema = os.getenv("CANONICAL_SCHEMA_PATH")
        if env_schema:
            args.schema = env_schema

    # Override environment variables if provided
    if args.database_url:
        os.environ['DATABASE_URL'] = args.database_url
    if args.embedding_database_url:
        os.environ['EMBEDDING_DATABASE_URL'] = args.embedding_database_url

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        return

    # Initialize AppContext singleton (same as API server)
    # This initializes all resources: LLM, embeddings, caches, schema analyzer
    from src.api.app_context import AppContext
    print("Initializing resources...")
    ctx = AppContext.get_instance()

    print(f"Processing: {query}")
    if args.schema:
        print(f"Using canonical schema: {args.schema}")
    if args.app:
        print(f"Application namespace: {args.app}")
    print("-" * 50)

    try:
        # Measure total pipeline execution time
        pipeline_start_time = time.time()

        # Prepare pipeline input
        pipeline_input = {
            "original_query": query,
            "show_explanation": args.explain,
            "export_csv": args.csv,
            "export_html": args.html,
            "execute": not args.sql_only,  # Execute by default, unless --sql-only is set
            "canonical_schema_path": args.schema,  # Pass canonical schema path if provided
        }

        result = await text_to_sql_graph.ainvoke(pipeline_input)
        
        pipeline_end_time = time.time()
        total_pipeline_time_ms = (pipeline_end_time - pipeline_start_time) * 1000
        
        # Add total pipeline time to result state for use in formatting
        result["total_pipeline_time_ms"] = total_pipeline_time_ms
        
        # Handle SQL-only mode differently
        if args.sql_only:
            sql = result.get("generated_sql", "No SQL generated")
            print("## Generated SQL")
            print(f"```sql\n{sql}\n```")
        else:
            response = result.get("formatted_response") or result.get("final_response", "No response generated")
            print(response)
        
        # Add total pipeline timing information with breakdown
        if total_pipeline_time_ms > 0:
            total_seconds = total_pipeline_time_ms / 1000
            print(f"\n⏱️  **Total time:** {total_seconds:.1f}s")
            
            # Show breakdown if available
            schema_time = result.get("schema_analysis_time_ms", 0.0)
            generation_time = result.get("sql_generation_time_ms", 0.0)
            interpretation_time = result.get("interpretation_time_ms", 0.0)
            db_time = result.get("execution_time_ms", 0.0)

            if any([schema_time, generation_time, interpretation_time]):
                print("   **Breakdown:**")
                if schema_time > 0:
                    print(f"   - Schema analysis: {schema_time/1000:.1f}s")
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
                    generation_time = result.get("sql_generation_time_ms", 0.0)
                    interpretation_time = result.get("interpretation_time_ms", 0.0)
                    db_time = result.get("execution_time_ms", 0.0)

                    timing_breakdown = f"\n\n**⏱️  Total time:** {total_seconds:.1f}s\n\n**Breakdown:**\n"
                    if schema_time > 0:
                        timing_breakdown += f"- Schema analysis: {schema_time/1000:.1f}s\n"
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
            except Exception as html_error:
                print(f"\n⚠️  HTML export failed: {html_error}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always clean up database connections
        cleanup_database_connections()

if __name__ == "__main__":
    asyncio.run(main())
