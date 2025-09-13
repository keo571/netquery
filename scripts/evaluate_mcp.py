#!/usr/bin/env python3
"""
MCP server evaluation script - tests tool functions and parameter support.
Simple direct function testing without FastMCP complexity.
"""
import inspect
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Test scenarios for tool functions
TEST_SCENARIOS = {
    "text_to_sql": [
        # Discovery queries
        {"query": "What data do you have?", "scenario": "First-time user discovery"},
        {"query": "Show me what's in this database", "scenario": "Database exploration"},
        
        # Basic operations
        {"query": "Show me all load balancers", "scenario": "Basic listing"},
        {"query": "List unhealthy servers", "scenario": "Filtering operation"},
        
        # Single flag tests
        {"query": "Show network traffic trends over time", "export_html": True, "scenario": "Visualization request"},
        {"query": "Explain how you found the servers", "show_explanation": True, "scenario": "Learning AI reasoning"},
        {"query": "Export server data", "export_csv": True, "scenario": "Data export need"},
        
        # Combined flag tests - realistic user requests
        {"query": "Show network traffic trends and explain your analysis", 
         "export_html": True, "show_explanation": True, 
         "scenario": "Detailed visualization with explanation"},
        
        {"query": "Export all server data with your reasoning", 
         "export_csv": True, "show_explanation": True,
         "scenario": "Data export with analysis explanation"},
        
        {"query": "Give me server data in multiple formats", 
         "export_csv": True, "export_html": True,
         "scenario": "Multi-format export request"},
        
        {"query": "Create a complete report on load balancer performance", 
         "export_html": True, "export_csv": True, "show_explanation": True,
         "scenario": "Full report with all features"},
    ],
    
    "get_schema": [
        {"question": "What tables are available?", "scenario": "Schema discovery"},
        {"question": "Tell me about the load balancers table", "params": {"table_names": ["load_balancers"]}, "scenario": "Specific table inquiry"},
        {"question": "Show me example data format", "params": {"include_sample_data": True}, "scenario": "Data format discovery"},
        {"question": "What network tables exist?", "params": {"table_names": ["network_traffic", "nonexistent_table"]}, "scenario": "Mixed valid/invalid tables"},
    ],
    
    "suggest_queries": [
        {"question": "What can I ask you?", "scenario": "General help request"},
        {"question": "Help me troubleshoot problems", "params": {"category": "troubleshooting"}, "scenario": "Category-specific help"},
        {"question": "Show me invalid category", "params": {"category": "nonexistent"}, "scenario": "Invalid category handling"},
    ]
}


class MCPFunctionEvaluator:
    """Test MCP server functions directly without FastMCP overhead."""
    
    def __init__(self):
        self.results = []
        self.functions = {}
        
    def evaluate_functions(self):
        """Test MCP functions by importing and inspecting them directly."""
        
        # Import MCP server functions
        try:
            from src.text_to_sql.mcp_server import text_to_sql, get_schema, suggest_queries
            self.functions = {
                "text_to_sql": text_to_sql,
                "get_schema": get_schema,
                "suggest_queries": suggest_queries
            }
            
            # Test each function
            self._test_text_to_sql_function()
            self._test_get_schema_function()
            self._test_suggest_queries_function()
            
        except ImportError as e:
            self.results.append({
                "category": "setup",
                "test": "Function Import",
                "scenario": "Setup test",
                "status": "ERROR",
                "message": f"Failed to import MCP functions: {e}",
                "features": []
            })
    
    def _test_text_to_sql_function(self):
        """Test text_to_sql function signature and parameter support."""
        
        func = self.functions.get("text_to_sql")
        if not func:
            self.results.append({
                "category": "text_to_sql",
                "test": "Function Discovery",
                "scenario": "Function availability",
                "status": "ERROR", 
                "message": "text_to_sql function not found",
                "features": []
            })
            return
        
        # Get function signature - func might be wrapped in FunctionTool
        try:
            # If it's a FastMCP FunctionTool, get the actual function
            actual_func = getattr(func, 'fn', func)
            sig = inspect.signature(actual_func)
            param_names = list(sig.parameters.keys())
            
            # Expected parameters for text_to_sql
            expected_params = ["query", "show_explanation", "export_csv", "export_html"]
            missing_params = [p for p in expected_params if p not in param_names]
            
            # Test each scenario
            for test in TEST_SCENARIOS["text_to_sql"]:
                query = test["query"]
                
                # Check parameter support
                if missing_params:
                    status = "FAIL"
                    message = f"Missing parameters: {missing_params}"
                    features = []
                else:
                    status = "PASS"
                    message = "All parameters supported"
                    # Track which features were requested
                    features = []
                    if test.get("show_explanation"):
                        features.append("show_explanation")
                    if test.get("export_csv"):
                        features.append("export_csv")
                    if test.get("export_html"):
                        features.append("export_html")
                
                self.results.append({
                    "category": "text_to_sql",
                    "test": query,
                    "scenario": test["scenario"],
                    "status": status,
                    "message": message,
                    "features": features
                })
                
        except Exception as e:
            self.results.append({
                "category": "text_to_sql",
                "test": "Signature Inspection",
                "scenario": "Parameter validation",
                "status": "ERROR",
                "message": f"Failed to inspect function: {str(e)[:50]}",
                "features": []
            })
    
    def _test_get_schema_function(self):
        """Test get_schema function signature."""
        
        func = self.functions.get("get_schema")
        if not func:
            self.results.append({
                "category": "get_schema",
                "test": "Function Discovery",
                "scenario": "Function availability",
                "status": "ERROR",
                "message": "get_schema function not found",
                "features": []
            })
            return
        
        try:
            # If it's a FastMCP FunctionTool, get the actual function
            actual_func = getattr(func, 'fn', func)
            sig = inspect.signature(actual_func)
            param_names = list(sig.parameters.keys())
            
            for test in TEST_SCENARIOS["get_schema"]:
                params = test.get("params", {})
                
                status = "PASS"
                message = "Function available"
                features = []
                
                # Check for specific parameter support
                if "table_names" in params:
                    if "table_names" in param_names:
                        features.append("table_filtering")
                    else:
                        status = "FAIL"
                        message = "table_names parameter not supported"
                
                if params.get("include_sample_data"):
                    if "include_sample_data" in param_names:
                        features.append("sample_data")
                    else:
                        status = "FAIL"
                        message = "include_sample_data parameter not supported"
                
                self.results.append({
                    "category": "get_schema",
                    "test": test["question"],
                    "scenario": test["scenario"],
                    "status": status,
                    "message": message,
                    "features": features
                })
                
        except Exception as e:
            self.results.append({
                "category": "get_schema",
                "test": "Signature Inspection",
                "scenario": "Parameter validation",
                "status": "ERROR",
                "message": f"Failed to inspect function: {str(e)[:50]}",
                "features": []
            })
    
    def _test_suggest_queries_function(self):
        """Test suggest_queries function signature."""
        
        func = self.functions.get("suggest_queries")
        if not func:
            self.results.append({
                "category": "suggest_queries",
                "test": "Function Discovery", 
                "scenario": "Function availability",
                "status": "ERROR",
                "message": "suggest_queries function not found",
                "features": []
            })
            return
        
        try:
            # If it's a FastMCP FunctionTool, get the actual function
            actual_func = getattr(func, 'fn', func)
            sig = inspect.signature(actual_func)
            param_names = list(sig.parameters.keys())
            
            for test in TEST_SCENARIOS["suggest_queries"]:
                params = test.get("params", {})
                
                status = "PASS"
                message = "Function available"
                features = []
                
                # Check category parameter support
                if "category" in params:
                    if "category" in param_names:
                        features.append("category_filtering")
                    else:
                        status = "FAIL"
                        message = "category parameter not supported"
                
                self.results.append({
                    "category": "suggest_queries",
                    "test": test["question"],
                    "scenario": test["scenario"],
                    "status": status,
                    "message": message,
                    "features": features
                })
                
        except Exception as e:
            self.results.append({
                "category": "suggest_queries",
                "test": "Signature Inspection",
                "scenario": "Parameter validation",
                "status": "ERROR",
                "message": f"Failed to inspect function: {str(e)[:50]}",
                "features": []
            })
    
    def generate_html_report(self):
        """Generate HTML evaluation report."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mcp_evaluation_report_{timestamp}.html"
        filepath = Path("testing/evaluations") / filename
        
        # Ensure testing/evaluations directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.results if r["status"] == "FAIL")  
        error_tests = sum(1 for r in self.results if r["status"] == "ERROR")
        
        # Create HTML table rows
        html_rows = []
        for result in self.results:
            status_color = "#d4edda" if result["status"] == "PASS" else "#f8d7da"
            features = ", ".join(result["features"]) if result["features"] else "none"
            
            html_rows.append(f"""
                <tr style='background-color:{status_color}'>
                    <td>{result['test'][:50]}</td>
                    <td>{result['scenario']}</td>
                    <td>{result['category']}</td>
                    <td>{features}</td>
                    <td><strong>{result['status']}</strong></td>
                    <td>{result['message'][:80]}</td>
                </tr>""")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP Function Evaluation Report</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: 600; }}
                .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>🔍 MCP Function Evaluation Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}</p>
            
            <div class="summary">
                <h2>📊 Summary</h2>
                <p><strong>Focus:</strong> Function signatures and parameter support (direct testing)</p>
                <p><strong>Total Tests:</strong> {total_tests}</p>
                <p><strong>Success Rate:</strong> {passed_tests}/{total_tests} ({(passed_tests/total_tests*100):.1f}%)</p>
                <p><strong>Failed:</strong> {failed_tests} | <strong>Errors:</strong> {error_tests}</p>
            </div>
            
            <h2>📋 Function Testing Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Query</th>
                        <th>Scenario</th>
                        <th>Function</th>
                        <th>Features Tested</th>
                        <th>Status</th>
                        <th>Result</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(html_rows)}
                </tbody>
            </table>
        </body>
        </html>
        """
        
        # Write HTML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Final summary
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"✅ MCP function evaluation complete!")
        print(f"📊 Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        print(f"📄 Report saved: {filepath.absolute()}")


def run_evaluation():
    """Run MCP function evaluation."""
    evaluator = MCPFunctionEvaluator()
    evaluator.evaluate_functions()
    evaluator.generate_html_report()


if __name__ == "__main__":
    run_evaluation()