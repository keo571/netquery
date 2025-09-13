# Netquery Evaluation Framework

This document describes the comprehensive evaluation system for testing and validating the Netquery text-to-SQL pipeline and MCP server functionality.

## Overview

The evaluation framework consists of two main components:

1. **Query Evaluation** (`scripts/evaluate_queries.py`) - Tests the core text-to-SQL pipeline across all query categories
2. **MCP Evaluation** (`scripts/evaluate_mcp.py`) - Tests MCP server tool selection and parameter handling

## Query Evaluation

### Purpose

The Query Evaluation framework tests the complete text-to-SQL pipeline end-to-end, measuring both technical success and behavioral accuracy across different query types and complexity levels.

### What It Tests

#### Query Categories (Aligned with SAMPLE_QUERIES.md)

1. **Basic Queries** - Simple table queries and filtering
   - "Show me all load balancers"
   - "List servers in maintenance"
   - "What SSL certificates do we have?"

2. **Analytics & Aggregations** - Counting, statistics, performance metrics
   - "How many load balancers do we have?"
   - "What's the average CPU utilization by datacenter?"
   - "Count servers by status"

3. **Multi-Table Joins** - Complex relationships and filtering
   - "Show load balancers with their backend servers"
   - "List unhealthy load balancers with high CPU servers"

4. **Time-Series & Visualization** - Charts and trend analysis
   - "Show network traffic trends over time"
   - "Display load balancer health scores over time"

5. **Troubleshooting** - Current status and problem identification
   - "Show certificates expiring in 30 days"
   - "Which servers have connection issues?"

6. **Edge Cases & Error Handling** - Invalid queries and safety validation
   - "Delete all servers" (should be blocked)
   - "Show me nonexistent table data"

### Metrics

#### Technical Success Rate
Percentage of queries that execute successfully through the entire pipeline:
```
Technical Success Rate = (Successful Queries / Total Queries) × 100%
```

#### Behavioral Accuracy
Percentage of queries that behave as expected (including appropriate failures):
```
Behavioral Accuracy = (Expected Behaviors / Total Queries) × 100%
```

**Expected Behaviors:**
- ✅ Normal queries should succeed
- ✅ Destructive queries should be blocked by safety validator
- ✅ Invalid/test queries should fail gracefully or return empty results
- ✅ Ambiguous queries should attempt a reasonable response

### Pipeline Stage Tracking

Each query is evaluated through all pipeline stages:

| Stage | Success Indicator | What It Measures |
|-------|------------------|------------------|
| **Schema** | ✅/❌ | Schema analysis and table selection |
| **SQL** | ✅/❌ | SQL query generation |
| **Execution** | ✅/❌ | Query execution and result retrieval |
| **Charts** | Type/None | Automatic chart generation |

### Output

- **Console Report** - Real-time progress and summary statistics
- **HTML Report** - Detailed results table saved to `testing/evaluations/`
- **File**: `query_evaluation_report_YYYYMMDD_HHMMSS.html`

### Usage

```bash
# Run complete evaluation
python scripts/evaluate_queries.py

# Check GEMINI_API_KEY is set
export GEMINI_API_KEY=your_key_here
python scripts/evaluate_queries.py
```

**Example Output:**
```
🚀 Starting Netquery Evaluation...
📊 Testing 52 queries across 6 categories

📂 Basic Queries (8 queries)
   1. Testing: Show me all load balancers
      ✅ SUCCESS (1.2s, 8 rows)
   
📈 EVALUATION SUMMARY
Technical Success Rate: 45/52 (86.5%)
Behavioral Accuracy: 48/52 (92.3%)
Charts Generated: 12
```

## MCP Evaluation

### Purpose

The MCP Evaluation framework tests the Model Context Protocol server implementation, focusing on tool discovery, parameter handling, and realistic usage scenarios.

### What It Tests

#### Tool Availability
- **text_to_sql** - Main query processing tool
- **get_schema** - Database schema information
- **suggest_queries** - Query suggestions by category

#### Parameter Handling
Tests each tool's parameter support and validation:

**text_to_sql parameters:**
- `query` (required) - Natural language query
- `show_explanation` (optional) - Detailed explanations
- `export_csv` (optional) - CSV export functionality  
- `export_html` (optional) - HTML report generation

**get_schema parameters:**
- `table_names` (optional) - Specific tables to describe
- `include_sample_data` (optional) - Include sample rows

**suggest_queries parameters:**
- `category` (optional) - Filter by query category

#### Realistic Usage Scenarios

1. **Single Feature Tests**
   - Basic querying without flags
   - Visualization requests (`export_html=True`)
   - Data export needs (`export_csv=True`)
   - Learning scenarios (`show_explanation=True`)

2. **Combined Feature Tests**
   - Visualization + explanation
   - Export + explanation  
   - Multi-format exports
   - Full reports with all features

3. **Tool Selection Tests**
   - Schema exploration workflows
   - Query suggestion requests
   - Complex multi-step operations

### Metrics

#### Tool Availability Rate
```
Availability Rate = (Available Tools / Expected Tools) × 100%
```

#### Parameter Support Rate
```
Parameter Support = (Supported Parameters / Expected Parameters) × 100%
```

#### Scenario Success Rate
```
Scenario Success = (Passing Scenarios / Total Scenarios) × 100%
```

### Output

- **Console Report** - Real-time test results and feature tracking
- **HTML Report** - Detailed test results saved to `testing/evaluations/`
- **File**: `mcp_evaluation_report_YYYYMMDD_HHMMSS.html`

### Usage

```bash
# Run MCP evaluation
python scripts/evaluate_mcp.py

# The script will test tool discovery and parameter handling
# No API key required (tests tool metadata only)
```

**Example Output:**
```
🔧 Starting MCP Server Evaluation...

Testing text_to_sql tool...
   ✅ Tool available and accessible
   ✅ All required parameters supported
   ✅ Complex scenario with all features: PASS

📊 MCP Evaluation Results:
Tool Availability: 3/3 (100%)
Parameter Support: 12/12 (100%)  
Scenario Success: 15/15 (100%)
```

## Comparison: Query vs MCP Evaluation

| Aspect | Query Evaluation | MCP Evaluation |
|--------|------------------|----------------|
| **Purpose** | End-to-end pipeline testing | Tool interface testing |
| **Scope** | SQL generation to results | Tool discovery to parameters |
| **Requirements** | GEMINI_API_KEY needed | No API key needed |
| **Focus** | Data accuracy & behavior | Interface compliance |
| **Runtime** | ~2-5 minutes | ~10-30 seconds |
| **Query Execution** | Actually runs queries | Tests tool metadata only |

## Best Practices

### When to Run Evaluations

1. **Before releases** - Ensure quality and compatibility
2. **After major changes** - Validate pipeline modifications  
3. **During development** - Catch regressions early
4. **Performance testing** - Monitor system capabilities

### Interpreting Results

#### Query Evaluation
- **>90% Technical Success** = Excellent pipeline performance
- **>85% Behavioral Accuracy** = Good error handling and safety
- **Charts Generated** = Visualization system working

#### MCP Evaluation  
- **100% Tool Availability** = MCP server properly configured
- **100% Parameter Support** = Complete tool interface
- **>95% Scenario Success** = Robust parameter handling

### Troubleshooting

#### Low Technical Success Rate
- Check database connectivity
- Verify GEMINI_API_KEY configuration
- Review SQL generation prompts
- Check for schema analysis issues

#### Low Behavioral Accuracy
- Review safety validator rules
- Check error handling in pipeline nodes
- Verify expected behavior logic in evaluation

#### MCP Tool Issues
- Confirm FastMCP server configuration
- Check tool function signatures
- Verify parameter type annotations

## Integration with Development

### Pre-commit Hooks
```bash
# Add to .git/hooks/pre-commit
python scripts/evaluate_mcp.py
if [ $? -ne 0 ]; then
    echo "MCP evaluation failed"
    exit 1
fi
```

### CI/CD Pipeline
```yaml
# Add to GitHub Actions
- name: Run Evaluations
  run: |
    python scripts/evaluate_mcp.py
    python scripts/evaluate_queries.py
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

### Performance Monitoring
- Track success rates over time
- Monitor query execution times
- Identify performance regressions
- Benchmark new features

---

## Files and Locations

- **Query Evaluation**: `scripts/evaluate_queries.py`
- **MCP Evaluation**: `scripts/evaluate_mcp.py`
- **Test Queries**: Defined in `docs/SAMPLE_QUERIES.md`
- **Reports**: Saved to `testing/evaluations/`
- **Configuration**: Uses `.env` for API keys

The evaluation framework ensures Netquery maintains high quality and reliability across all use cases and deployment scenarios.