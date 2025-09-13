#!/usr/bin/env python3
"""
Comprehensive query evaluation framework aligned with SAMPLE_QUERIES.md structure.
Tests representative queries across all categories and functionality.

Categories evaluated:
- Basic Queries: Simple table queries and basic filtering
- Analytics & Aggregations: Counting, statistics, and performance metrics  
- Multi-Table Joins: Infrastructure relationships and complex filtering
- Time-Series & Visualization: Charts and trend analysis
- Troubleshooting: Current status checks and problem identification
- Edge Cases & Error Handling: Invalid queries and safety validation
"""
import asyncio
import time
import os
import sys
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

from src.text_to_sql.pipeline.graph import text_to_sql_graph


# Query categories aligned with reorganized SAMPLE_QUERIES.md
EVALUATION_QUERIES = {
    "Basic Queries": [
        "Show me all load balancers",
        "List all servers",
        "What SSL certificates do we have?",
        "Display VIP pools",
        "Show unhealthy load balancers",
        "List servers in maintenance",
        "Show servers with high CPU usage",
        "List load balancers in us-east-1",
    ],
    
    "Analytics & Aggregations": [
        "How many load balancers do we have?",
        "Count servers by datacenter",
        "What's the average CPU utilization by datacenter?",
        "Show server count grouped by status",
        "Count SSL certificates by provider",
        "What's the average memory usage by server role?",
        "Show load balancer distribution by type",
        "What's the total bandwidth consumption?",
    ],
    
    "Multi-Table Joins": [
        "Show load balancers with their backend servers and current status",
        "List servers with their load balancer connections and roles",
        "Find load balancers with their VIP pool configurations",
        "Show unhealthy load balancers in us-east-1 with their backend servers that have high CPU usage",
        "Show servers with high packet loss and their network connectivity details",
        "List load balancers with their VIP pools and average traffic statistics",
    ],
    
    "Time-Series & Visualization": [
        "Show network traffic trends over time",
        "Show backend health trends over time",
        "Display load balancer health scores over time",
        "Show server performance by datacenter",
        "Display load balancer types distribution",
        "Show CPU vs memory usage",
        "Display response time vs error rate",
    ],
    
    "Troubleshooting": [
        "Show certificates expiring in the next 30 days",
        "List current SSL monitoring status",
        "Show all unhealthy infrastructure",
        "What's the health status by datacenter?",
        "Find servers with connection issues",
        "Which servers have the highest CPU utilization?",
        "Which SSL certificates need renewal?",
    ],
    
    "Edge Cases & Error Handling": [
        "Show me nonexistent table data",
        "List servers in Mars datacenter",
        "Delete all servers",
        "Show me everything",
        "What's broken?",
        "Give me a summary",
    ]
}


class QueryEvaluator:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.summary: Dict[str, int] = {
            "total": 0,
            "success": 0,
            "schema_fail": 0,
            "sql_fail": 0,
            "exec_fail": 0,
            "charts_generated": 0
        }
    
    async def evaluate_query(self, query: str, category: str) -> Dict[str, Any]:
        """Evaluate a single query and return results."""
        result = {
            "query": query[:50] + "..." if len(query) > 50 else query,
            "full_query": query,
            "category": category,
            "schema": "❌",
            "sql": "❌", 
            "execution": "❌",
            "rows": 0,
            "chart": "none",
            "time": 0.0,
            "status": "UNKNOWN",
            "error": "",
            "expected": False
        }
        
        start_time = time.time()
        
        try:
            # Run the pipeline
            pipeline_result = await text_to_sql_graph.ainvoke({
                "original_query": query,
                "include_explanation": False,
                "save_csv": False
            })
            
            result["time"] = time.time() - start_time
            
            # Check pipeline stages
            if pipeline_result.get("schema_context"):
                result["schema"] = "✅"
                
            if pipeline_result.get("generated_sql"):
                result["sql"] = "✅"
                
            if pipeline_result.get("query_results") is not None:
                result["execution"] = "✅"
                result["rows"] = len(pipeline_result.get("query_results", []))
                
            # Check for charts
            chart_html = pipeline_result.get("chart_html", "")
            if chart_html:
                result["chart"] = self._detect_chart_type(chart_html)
                
            # Determine final status
            if pipeline_result.get("execution_error"):
                result["status"] = "EXEC_FAIL"
                result["error"] = str(pipeline_result["execution_error"])[:100]
            elif pipeline_result.get("generation_error"):
                result["status"] = "SQL_FAIL" 
                result["error"] = str(pipeline_result["generation_error"])[:100]
            elif pipeline_result.get("schema_analysis_error"):
                result["status"] = "SCHEMA_FAIL"
                result["error"] = str(pipeline_result["schema_analysis_error"])[:100]
            elif result["execution"] == "✅":
                result["status"] = "SUCCESS"
            else:
                result["status"] = "UNKNOWN"
            
            # Determine if response was expected behavior
            result["expected"] = self._check_expected_behavior(query, result["status"], result.get("error", ""))
                
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
    
    def _check_expected_behavior(self, query: str, status: str, error: str) -> bool:
        """Check if the system behavior was expected for this query type."""
        query_lower = query.lower()
        error_lower = error.lower()
        
        # Destructive queries should be blocked
        if any(word in query_lower for word in ["delete", "drop", "update", "truncate"]):
            return "safety" in error_lower or "blocked" in error_lower
        
        # Invalid/test queries should fail gracefully  
        if any(word in query_lower for word in ["mars", "nonexistent", "fake"]):
            return status in ["EXEC_FAIL", "SCHEMA_FAIL", "SUCCESS"]  # SUCCESS with 0 rows is also valid
        
        # Ambiguous queries - any attempt to respond is expected
        if any(phrase in query_lower for phrase in ["what's broken", "everything", "give me a summary"]):
            return True  # Any response is acceptable
        
        # Normal queries should succeed
        return status == "SUCCESS"
    
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
                elif result["status"] == "SQL_FAIL":
                    self.summary["sql_fail"] += 1
                elif result["status"] == "EXEC_FAIL":
                    self.summary["exec_fail"] += 1
                    
                if result["chart"] != "none":
                    self.summary["charts_generated"] += 1
                
                # Track expected behavior
                if "expected_behavior" not in self.summary:
                    self.summary["expected_behavior"] = 0
                if result["expected"]:
                    self.summary["expected_behavior"] += 1
                    
                # Show status
                status_icon = "✅" if result["status"] == "SUCCESS" else "❌"
                chart_info = f" [{result['chart']}]" if result["chart"] != "none" else ""
                print(f"      {status_icon} {result['status']} ({result['time']:.1f}s, {result['rows']} rows{chart_info})")
        
        self._print_summary()
        self._save_detailed_report()
    
    def _print_summary(self):
        """Print evaluation summary."""
        print("\n" + "=" * 80)
        print("📈 EVALUATION SUMMARY")
        print("=" * 80)
        
        total = self.summary["total"]
        technical_success_rate = (self.summary["success"] / total * 100) if total > 0 else 0
        behavioral_accuracy = (self.summary.get("expected_behavior", 0) / total * 100) if total > 0 else 0
        
        print(f"\n📊 Key Metrics:")
        print(f"  Technical Success Rate: {self.summary['success']}/{total} ({technical_success_rate:.1f}%)")
        print(f"  Behavioral Accuracy:    {self.summary.get('expected_behavior', 0)}/{total} ({behavioral_accuracy:.1f}%)")
        
        print(f"\n📈 Breakdown:")
        print(f"  Total Queries:      {total}")
        print(f"  Successful:         {self.summary['success']}")
        print(f"  Schema Failures:    {self.summary['schema_fail']}")
        print(f"  SQL Failures:       {self.summary['sql_fail']}")
        print(f"  Execution Failures: {self.summary['exec_fail']}")
        print(f"  Charts Generated:   {self.summary['charts_generated']}")
        
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"query_evaluation_report_{timestamp}.html"
        
        # Create HTML table
        html_rows = []
        for result in self.results:
            status_color = "#d4edda" if result["status"] == "SUCCESS" else "#f8d7da"
            chart_badge = f"<span style='background:#007bff;color:white;padding:2px 6px;border-radius:3px;font-size:11px'>{result['chart']}</span>" if result["chart"] != "none" else ""
            
            html_rows.append(f"""
            <tr style="background-color: {status_color};">
                <td>{result['query']}</td>
                <td><span style='background:#6c757d;color:white;padding:2px 6px;border-radius:3px;font-size:11px'>{result['category']}</span></td>
                <td>{result['schema']}</td>
                <td>{result['sql']}</td>
                <td>{result['execution']}</td>
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
            </style>
        </head>
        <body>
            <h1>🚀 Netquery Evaluation Report</h1>
            <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            
            <div class="summary">
                <h2>📊 Key Metrics</h2>
                <p><strong>Technical Success Rate:</strong> {self.summary['success']}/{self.summary['total']} ({(self.summary['success']/self.summary['total']*100):.1f}%) - Queries that executed successfully</p>
                <p><strong>Behavioral Accuracy:</strong> {self.summary.get('expected_behavior', 0)}/{self.summary['total']} ({(self.summary.get('expected_behavior', 0)/self.summary['total']*100 if self.summary['total'] > 0 else 0):.1f}%) - Queries handled correctly (including appropriate failures)</p>
                <hr style="margin: 15px 0;">
                <p><strong>Total Queries:</strong> {self.summary['total']}</p>
                <p><strong>Charts Generated:</strong> {self.summary['charts_generated']}</p>
            </div>
            
            <h2>📋 Detailed Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Query</th>
                        <th>Category</th>
                        <th>Schema</th>
                        <th>SQL</th>
                        <th>Execution</th>
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
        print(f"📂 Reports directory: {report_dir.absolute()}")


async def main():
    """Run the evaluation."""
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("Please set your API key before running evaluation")
        return
        
    evaluator = QueryEvaluator()
    await evaluator.run_evaluation()


if __name__ == "__main__":
    asyncio.run(main())