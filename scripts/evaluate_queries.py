#!/usr/bin/env python3
"""
Comprehensive query evaluation framework with both single query and batch testing modes.

Usage:
  python scripts/evaluate_queries.py                           # Batch test all queries with HTML report
  python scripts/evaluate_queries.py --single "your query"     # Test single query (pass/fail only)

Batch testing includes:
- HTML report generation
- Comprehensive pipeline statistics
- Chart generation tracking
- Performance metrics

Single query testing includes:
- Console-only output
- Pass/fail status
- Error reporting for failures
"""
import asyncio
import time
import os
import sys
import argparse
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

from src.text_to_sql.pipeline.graph import text_to_sql_graph


# Comprehensive Text-to-SQL evaluation queries (49 total)
EVALUATION_QUERIES = {
    "Basic Queries": [
        "Show me all load balancers",
        "List all servers",
        "What SSL certificates do we have?",
        "Display VIP pools",
        "List servers in us-east-1",
    ],

    "Aggregations": [
        "How many load balancers do we have?",
        "Count servers by datacenter",
        "What's the average CPU utilization by datacenter?",
        "What's the total bandwidth consumption?",
        "Show top 3 load balancers by traffic volume in each region",
    ],

    "Comparative Queries": [
        "Which servers have higher CPU than average?",
        "Find load balancers with more backends than typical",
        "Show datacenters with above-average server counts",
    ],

    "Multi-Table Joins": [
        "Show load balancers with their backend servers and current status",
        "List servers with their load balancer connections and roles",
        "Show load balancers with backend mappings and monitoring metrics",
        "Find servers with their monitoring data and SSL certificate status",
        "Show servers with their load balancers and SSL certificate details",
    ],

    "Set Operations & Existence": [
        "Are there any servers without SSL certificates?",
        "Find load balancers with no backend servers assigned",
        "Show servers that have never been monitored",
    ],

    "Conditional Logic": [
        "Categorize servers as High/Medium/Low based on CPU usage",
        "Show load balancers with traffic status (Heavy/Normal/Light)",
        "Display server health as Critical/Warning/OK based on metrics",
    ],

    "HAVING & Advanced Filters": [
        "Show datacenters with more than 5 unhealthy servers",
        "Find load balancers where average response time exceeds 500ms",
        "List SSL providers managing more than 10 certificates",
    ],

    "Window Functions & Analytics": [
        "Rank servers by CPU utilization within each datacenter",
        "Compare each server's current CPU to its previous measurement",
        "Calculate moving average of response times over the last 5 measurements",
    ],

    "Time-based Queries": [
        "Show certificates expiring in the next 30 days",
        "Find servers with high CPU for the last 3 consecutive monitoring periods",
        "Show network traffic trends over the past week",
    ],

    "Troubleshooting": [
        "What's the health status by datacenter?",
        "Find servers with connection issues",
    ],

    "Performance Testing": [
        "Show all monitoring metrics without any filtering",
        "Display comprehensive server details with all related data",
    ],

    "Subqueries & Advanced Patterns": [
        "Find servers in datacenters that have more than 5 load balancers",
        "Show load balancers with more backends than the average",
        "List servers that are monitored but not assigned to any load balancer",
    ],

    "String Operations & NULL Handling": [
        "Find servers with hostnames containing 'web'",
        "Show certificates with domains ending in '.com'",
        "Display servers where hostname is not recorded",
        "List load balancers with missing health score data",
    ],

    "Edge Cases": [
        "Show me nonexistent table data",
        "List servers in Mars datacenter",
        "Delete all servers",
        "Show me everything",
        "What's broken?",
    ]
}


class QueryEvaluator:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.summary: Dict[str, int] = {
            "total": 0,
            "success": 0,
            "schema_fail": 0,
            "plan_fail": 0,
            "gen_fail": 0,
            "valid_fail": 0,
            "exec_fail": 0,
            "unknown_fail": 0,
            "timeout": 0,
            "error": 0,
            "charts_generated": 0
        }
    
    async def evaluate_query(self, query: str, category: str) -> Dict[str, Any]:
        """Evaluate a single query and return results."""
        result = {
            "query": query[:80] + "..." if len(query) > 80 else query,
            "full_query": query,
            "category": category,
            "rows": 0,
            "chart": "none",
            "time": 0.0,
            "status": "UNKNOWN",
            "error": ""
        }
        
        start_time = time.time()
        
        try:
            # Run the pipeline with timeout
            pipeline_result = await asyncio.wait_for(
                text_to_sql_graph.ainvoke({
                    "original_query": query,
                    "show_explanation": False,
                    "export_csv": False,
                    "export_html": False
                }),
                timeout=30.0  # 30 second timeout
            )
            
            result["time"] = time.time() - start_time

            # Get query results and row count
            if pipeline_result.get("query_results") is not None:
                result["rows"] = len(pipeline_result.get("query_results", []))

            # Check for charts
            chart_html = pipeline_result.get("chart_html", "")
            if chart_html:
                result["chart"] = self._detect_chart_type(chart_html)
                
            # Determine final status (matching single query mode)
            if pipeline_result.get("execution_error"):
                result["status"] = "EXEC_FAIL"
                result["error"] = str(pipeline_result["execution_error"])[:100]
            elif pipeline_result.get("validation_error"):
                result["status"] = "VALID_FAIL"
                result["error"] = str(pipeline_result["validation_error"])[:100]
            elif pipeline_result.get("generation_error"):
                result["status"] = "GEN_FAIL"
                result["error"] = str(pipeline_result["generation_error"])[:100]
            elif pipeline_result.get("planning_error"):
                result["status"] = "PLAN_FAIL"
                result["error"] = str(pipeline_result["planning_error"])[:100]
            elif pipeline_result.get("schema_analysis_error"):
                result["status"] = "SCHEMA_FAIL"
                result["error"] = str(pipeline_result["schema_analysis_error"])[:100]
            elif 'formatted_response' in pipeline_result:
                result["status"] = "SUCCESS"
            else:
                result["status"] = "UNKNOWN_FAIL"
            
                
        except asyncio.TimeoutError:
            result["time"] = 30.0  # Timeout duration
            result["status"] = "TIMEOUT"
            result["error"] = "Query execution timed out after 30 seconds"

        except Exception as e:
            result["time"] = time.time() - start_time
            result["status"] = "ERROR"
            result["error"] = str(e)[:100]
            
        return result
    
    def _detect_chart_type(self, chart_html: str) -> str:
        """Detect chart type from HTML."""
        if not chart_html:
            return "none"
        elif "Over Time" in chart_html:
            return "line"
        elif "by Category" in chart_html:
            return "bar" 
        elif " vs " in chart_html:
            return "scatter"
        elif "Distribution" in chart_html:
            return "pie"
        else:
            return "unknown"
    
    
    async def run_evaluation(self):
        """Run evaluation on all queries."""
        print("🚀 Starting Netquery Evaluation...")
        print(f"📊 Testing {sum(len(queries) for queries in EVALUATION_QUERIES.values())} queries across {len(EVALUATION_QUERIES)} categories")
        print("=" * 80)
        
        for category, queries in EVALUATION_QUERIES.items():
            print(f"\n📂 {category} ({len(queries)} queries)")
            
            for i, query in enumerate(queries, 1):
                print(f"   {i:2d}. Testing: {query[:60]}{'...' if len(query) > 60 else ''}")
                
                result = await self.evaluate_query(query, category)
                self.results.append(result)
                
                # Update summary
                self.summary["total"] += 1
                if result["status"] == "SUCCESS":
                    self.summary["success"] += 1
                elif result["status"] == "SCHEMA_FAIL":
                    self.summary["schema_fail"] += 1
                elif result["status"] == "PLAN_FAIL":
                    self.summary["plan_fail"] += 1
                elif result["status"] == "GEN_FAIL":
                    self.summary["gen_fail"] += 1
                elif result["status"] == "VALID_FAIL":
                    self.summary["valid_fail"] += 1
                elif result["status"] == "EXEC_FAIL":
                    self.summary["exec_fail"] += 1
                elif result["status"] == "UNKNOWN_FAIL":
                    self.summary["unknown_fail"] += 1
                elif result["status"] == "TIMEOUT":
                    self.summary["timeout"] += 1
                elif result["status"] == "ERROR":
                    self.summary["error"] += 1

                if result["chart"] != "none":
                    self.summary["charts_generated"] += 1
                    
                # Show status
                status_icon = "✅" if result["status"] == "SUCCESS" else "⏱️" if result["status"] == "TIMEOUT" else "❌"
                chart_info = f" [{result['chart']}]" if result["chart"] != "none" else ""
                if result["status"] == "TIMEOUT":
                    print(f"      {status_icon} {result['status']} ({result['time']:.1f}s) - {result['error']}")
                else:
                    print(f"      {status_icon} {result['status']} ({result['time']:.1f}s, {result['rows']} rows{chart_info})")
        
        self._print_summary()
        self._save_detailed_report()
    
    def _print_summary(self):
        """Print evaluation summary."""
        print("\n" + "=" * 80)
        print("📈 EVALUATION SUMMARY")
        print("=" * 80)
        
        total = self.summary["total"]
        success_rate = (self.summary["success"] / total * 100) if total > 0 else 0

        print(f"\n📊 Key Metrics:")
        print(f"  Overall Success Rate: {self.summary['success']}/{total} ({success_rate:.1f}%)")
        print(f"  Charts Generated:     {self.summary['charts_generated']}")

        print(f"\n🔧 Failure Breakdown:")
        print(f"  Schema Failures:    {self.summary['schema_fail']}")
        print(f"  Planning Failures:  {self.summary['plan_fail']}")
        print(f"  Generation Failures: {self.summary['gen_fail']}")
        print(f"  Validation Failures: {self.summary['valid_fail']}")
        print(f"  Execution Failures: {self.summary['exec_fail']}")
        print(f"  Unknown Failures:   {self.summary['unknown_fail']}")
        print(f"  Timeouts:           {self.summary['timeout']}")
        print(f"  System Errors:      {self.summary['error']}")

        print(f"\n📈 By Category:")
        category_stats = {}
        for result in self.results:
            cat = result["category"]
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "success": 0}
            category_stats[cat]["total"] += 1
            if result["status"] == "SUCCESS":
                category_stats[cat]["success"] += 1

        # Use EVALUATION_QUERIES order instead of alphabetical
        for category in EVALUATION_QUERIES.keys():
            if category in category_stats:
                stats = category_stats[category]
                rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
                print(f"  {category}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
        
        # Chart breakdown
        chart_types = {}
        for result in self.results:
            if result["chart"] != "none":
                chart_types[result["chart"]] = chart_types.get(result["chart"], 0) + 1
        
        if chart_types:
            print(f"\nChart Types:")
            for chart_type, count in sorted(chart_types.items()):
                print(f"  {chart_type}: {count}")
    
    def _save_detailed_report(self):
        """Save detailed HTML report."""
        # Create testing/evaluations directory
        from pathlib import Path
        report_dir = Path(__file__).parent.parent / "testing" / "evaluations"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = report_dir / "query_evaluation_report.html"
        
        # Create HTML table
        html_rows = []
        for result in self.results:
            status_color = "#d4edda" if result["status"] == "SUCCESS" else "#f8d7da"
            chart_badge = f"<span style='background:#007bff;color:white;padding:2px 6px;border-radius:3px;font-size:11px'>{result['chart']}</span>" if result["chart"] != "none" else ""
            
            html_rows.append(f"""
            <tr style="background-color: {status_color};">
                <td>{result['query']}</td>
                <td><span style='background:#6c757d;color:white;padding:2px 6px;border-radius:3px;font-size:11px'>{result['category']}</span></td>
                <td>{result['rows']}</td>
                <td>{chart_badge}</td>
                <td>{result['time']:.1f}s</td>
                <td><strong>{result['status']}</strong></td>
            </tr>""")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Netquery Evaluation Report</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                .summary {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #007bff; }}
            </style>
        </head>
        <body>
            <h1>🚀 Netquery Evaluation Report</h1>
            <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            
            <div class="summary">
                <h2>📊 Summary Metrics</h2>
                <div class="metric">
                    <strong>Overall Success Rate</strong><br>
                    {(self.summary['success']/self.summary['total']*100):.1f}% ({self.summary['success']}/{self.summary['total']})
                </div>
                <div class="metric">
                    <strong>Charts Generated</strong><br>
                    {self.summary['charts_generated']} charts
                </div>
            </div>

            <h2>📈 Results by Category</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Total Tests</th>
                        <th>Correct</th>
                        <th>Accuracy</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(self._generate_category_html())}
                </tbody>
            </table>
            
            <h2>📋 Detailed Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Query</th>
                        <th>Category</th>
                        <th>Rows</th>
                        <th>Chart</th>
                        <th>Time</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(html_rows)}
                </tbody>
            </table>
        </body>
        </html>
        """
        
        Path(report_path).write_text(html_content)
        print(f"\n📄 Detailed report saved: {report_path}")

    def _generate_category_html(self):
        """Generate HTML table rows for category breakdown matching evaluator.py format."""
        category_stats = {}
        for result in self.results:
            cat = result["category"]
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "success": 0}
            category_stats[cat]["total"] += 1
            if result["status"] == "SUCCESS":
                category_stats[cat]["success"] += 1

        html_rows = []
        # Use EVALUATION_QUERIES order instead of alphabetical
        for category in EVALUATION_QUERIES.keys():
            if category in category_stats:
                stats = category_stats[category]
                rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
                html_rows.append(f"""
            <tr>
                <td>{category}</td>
                <td>{stats['total']}</td>
                <td>{stats['success']}</td>
                <td>{rate:.1f}%</td>
            </tr>""")

        return html_rows


def test_single_query(query: str):
    """Test a single query through the pipeline (pass/fail only)."""
    print(f"🔍 Testing query: {query}")
    print("=" * 60)

    try:
        result = text_to_sql_graph.invoke({
            'original_query': query,
            'show_explanation': False,
            'export_csv': False,
            'export_html': False
        })

        if 'formatted_response' in result:
            print("✅ SUCCESS")

        elif 'final_response' in result:
            # Determine specific failure type
            if 'schema_analysis_error' in result:
                print("❌ SCHEMA_FAIL")
                print(f"🔍 Schema analysis error: {result['schema_analysis_error']}")
            elif 'planning_error' in result:
                print("❌ PLAN_FAIL")
                print(f"📋 Planning error: {result['planning_error']}")
            elif 'generation_error' in result:
                print("❌ GEN_FAIL")
                print(f"🔧 Generation error: {result['generation_error']}")
            elif 'validation_error' in result:
                print("❌ VALID_FAIL")
                print(f"✅ Validation error: {result['validation_error']}")
            elif 'execution_error' in result:
                print("❌ EXEC_FAIL")
                print(f"⚡ Execution error: {result['execution_error']}")
            else:
                print("❌ UNKNOWN_FAIL")

        else:
            print("❌ ERROR")
            print("Available keys:", list(result.keys()))

    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run the evaluation with command-line argument support."""
    parser = argparse.ArgumentParser(
        description="Text-to-SQL Query Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/evaluate_queries.py                           # Batch test all queries with HTML report
  python scripts/evaluate_queries.py --single "Show all servers"  # Test single query (pass/fail only)
        """
    )

    parser.add_argument(
        "--single",
        type=str,
        help="Test a single query (pass/fail only, no HTML report)"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("Please set your API key before running evaluation")
        return

    if args.single:
        # Single query mode - pass/fail only
        print("🔧 Single Query Mode")
        test_single_query(args.single)
    else:
        # Batch testing mode - HTML report generation
        print("📊 Batch Evaluation Mode")
        evaluator = QueryEvaluator()
        await evaluator.run_evaluation()


if __name__ == "__main__":
    asyncio.run(main())