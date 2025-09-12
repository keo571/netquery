#!/usr/bin/env python3
"""
Batch evaluation script for SAMPLE_QUERIES.md
Tests representative queries across all categories and functionality.
"""
import asyncio
import time
import os
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.text_to_sql.pipeline.graph import text_to_sql_graph


# Representative queries from SAMPLE_QUERIES.md
EVALUATION_QUERIES = {
    "Basic Operations": [
        "Show me all load balancers",
        "List all servers",
        "Display VIP pools",
        "Show network traffic data",
    ],
    
    "Filtering & Conditions": [
        "Show me unhealthy load balancers",
        "Show me load balancers in us-east-1",
        "Show me servers with CPU usage above 80%",
        "Show traffic with more than 1000 requests per second",
    ],
    
    "Analytics & Aggregations": [
        "How many load balancers do we have?",
        "Count unhealthy servers by datacenter",
        "Show me server count grouped by status",
        "What's the average memory usage by datacenter?",
    ],
    
    "Line Charts": [
        "Show network traffic for load balancer 1 over time",
        "Show backend health trends over time",
    ],
    
    "Bar Charts": [
        "Show server performance by datacenter",
        "Display load balancer types distribution", 
        "Show server count grouped by status",
    ],
    
    "Scatter Plots": [
        "Show CPU utilization and memory usage for all servers",
        "Show bandwidth vs request volume",
    ],
    
    "Complex Queries": [
        "Show me load balancers with their backend servers",
        "List VIP pools with their load balancers",
    ],
    
    "Edge Cases": [
        "Show me nonexistent table data",
        "List servers in Mars datacenter",
        "Delete all servers",
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
            "error": ""
        }
        
        start_time = time.time()
        
        try:
            # Run the pipeline
            pipeline_result = await text_to_sql_graph.ainvoke({
                "original_query": query,
                "include_reasoning": False,
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
                elif result["status"] == "SQL_FAIL":
                    self.summary["sql_fail"] += 1
                elif result["status"] == "EXEC_FAIL":
                    self.summary["exec_fail"] += 1
                    
                if result["chart"] != "none":
                    self.summary["charts_generated"] += 1
                    
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
        success_rate = (self.summary["success"] / total * 100) if total > 0 else 0
        
        print(f"Total Queries:     {total}")
        print(f"Successful:        {self.summary['success']} ({success_rate:.1f}%)")
        print(f"Schema Failures:   {self.summary['schema_fail']}")
        print(f"SQL Failures:      {self.summary['sql_fail']}")
        print(f"Execution Failures: {self.summary['exec_fail']}")
        print(f"Charts Generated:  {self.summary['charts_generated']}")
        
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"evaluation_report_{timestamp}.html"
        
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
                <h2>📊 Summary</h2>
                <p><strong>Total Queries:</strong> {self.summary['total']}</p>
                <p><strong>Success Rate:</strong> {self.summary['success']}/{self.summary['total']} ({(self.summary['success']/self.summary['total']*100):.1f}%)</p>
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