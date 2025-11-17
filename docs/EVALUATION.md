# Netquery Query Evaluation Framework

This document describes the comprehensive evaluation system for testing and validating the Netquery text-to-SQL pipeline using `testing/evaluate_queries.py`.

## Purpose

The Query Evaluation framework tests the complete text-to-SQL pipeline end-to-end, measuring technical success across different query types and complexity levels.

## Test Query Sets

The evaluation framework uses environment-specific query sets stored in JSON files:

- **Dev Mode (SQLite)**: `testing/query_sets/dev.json` - 80+ queries testing SQLite database
- **Prod Mode (PostgreSQL)**: `testing/query_sets/prod.json` - 90+ queries testing PostgreSQL database

### Dev Mode Query Categories

Tests for SQLite database with SSL certificates, network monitoring, and detailed health tracking:

1. **Basic Queries** - Simple table queries and filtering
2. **Health & Status** - Server health, load balancer scores, SSL status
3. **Aggregations** - Counting, statistics, averages
4. **Traffic & Performance** - Network traffic, response times, error rates
5. **Multi-Table Joins** - Complex relationships across tables
6. **SSL Certificate Management** - Certificate expiry, issuers, monitoring (dev only)
7. **Network Monitoring** - Latency, packet loss, connectivity (dev only)
8. **Time-based Queries** - Trends, historical data, time-series
9. **Comparative & Advanced** - Above/below average, complex filtering
10. **HAVING & Filters** - Aggregate filtering, group conditions
11. **Existence & NULL Checks** - Missing data, orphaned records
12. **String Operations** - Pattern matching, text search
13. **Conditional Logic** - CASE statements, categorization
14. **Complex Analytics** - Multi-table comprehensive analysis
15. **Edge Cases** - Error handling, invalid queries, safety checks

### Prod Mode Query Categories

Tests for PostgreSQL database with wide IPs and global load balancing:

1. **Basic Queries** - Simple table queries
2. **Inventory & Filtering** - Resource discovery and filtering
3. **Status & Health** - Backend server and load balancer health
4. **Aggregations & Summaries** - Counting and distribution
5. **Relationship Queries** - Joins across core tables
6. **Wide IP & Global Load Balancing** - Global routing, DNS (prod only)
7. **Traffic Analysis** - Traffic statistics and metrics (prod only)
8. **Multi-Table Joins** - Complex hierarchical relationships
9. **Comparative & Advanced** - Above/below average analysis
10. **HAVING & Aggregation Filters** - Aggregate conditions
11. **Existence & NULL Checks** - Missing associations
12. **String Operations** - Text search and patterns
13. **Conditional Logic** - Categorization and classification
14. **Time-based Queries** - Temporal data and trends
15. **Complex Analytics** - Comprehensive multi-table analysis
16. **Edge Cases** - Error handling and safety validation

## Metrics

### Technical Success Rate
Percentage of queries that execute successfully through the entire pipeline:
```
Technical Success Rate = (Successful Queries / Total Queries) × 100%
```

### Pipeline Stage Tracking

Each query is evaluated through all pipeline stages:

| Stage | Status | What It Measures |
|-------|--------|------------------|
| **Schema Analysis** | SUCCESS/SCHEMA_FAIL | Schema analysis and table selection |
| **SQL Generation** | SUCCESS/GEN_FAIL | SQL query generation from natural language |
| **SQL Validation** | SUCCESS/VALID_FAIL | SQL syntax and safety validation |
| **Query Execution** | SUCCESS/EXEC_FAIL | Query execution and result retrieval |
| **Chart Generation** | Type/None | Automatic visualization detection |

### Failure Breakdown

- **SCHEMA_FAIL**: Schema analysis errors (table/column not found)
- **GEN_FAIL**: SQL generation failures (LLM unable to generate valid SQL)
- **VALID_FAIL**: SQL validation failures (syntax, safety)
- **EXEC_FAIL**: Execution errors (database errors, timeouts)
- **UNKNOWN_FAIL**: Other pipeline failures
- **TIMEOUT**: Query timeout (>30 seconds)
- **ERROR**: System errors and exceptions

## Usage

### Batch Evaluation (All Queries)

Run comprehensive evaluation with HTML report:

```bash
# Evaluate dev mode queries (SQLite)
python testing/evaluate_queries.py

# Evaluate prod mode queries (PostgreSQL)
NETQUERY_ENV=prod python testing/evaluate_queries.py

# Use custom query file
python testing/evaluate_queries.py --queries /path/to/queries.json
```

**Output**:
- Console progress and summary
- HTML report: `testing/evaluations/query_evaluation_report.html`

### Single Query Testing

Test individual queries for quick validation:

```bash
# Test a single query (dev mode)
python testing/evaluate_queries.py --single "Show all load balancers"

# Test a single query (prod mode)
NETQUERY_ENV=prod python testing/evaluate_queries.py --single "List all virtual IPs"
```

**Output**: Console-only pass/fail status with error details

### Environment Setup

Ensure API key is configured:

```bash
export GEMINI_API_KEY=your_key_here
```

Or set in `.env` file:
```bash
GEMINI_API_KEY=your_key_here
```

## Output Examples

### Batch Evaluation Output

```
🚀 Starting Netquery Evaluation...
   Environment: dev
   Query file:  testing/query_sets/dev.json
📊 Testing 85 queries across 15 categories
================================================================================

📂 Basic Queries (6 queries)
   1. Testing: Show me all load balancers
      ✅ SUCCESS (1.2s, 30 rows)
   2. Testing: List all servers
      ✅ SUCCESS (0.8s, 30 rows)
   ...

📂 SSL Certificate Management (5 queries)
   1. Testing: Show certificates expiring in the next 30 days
      ✅ SUCCESS (1.5s, 8 rows) [bar]
   ...

================================================================================
📈 EVALUATION SUMMARY
================================================================================

📊 Key Metrics:
  Overall Success Rate: 72/85 (84.7%)
  Charts Generated:     18

🔧 Failure Breakdown:
  Schema Failures:    2
  Planning Failures:  3
  Generation Failures: 4
  Validation Failures: 1
  Execution Failures: 2
  Unknown Failures:   1
  Timeouts:           0
  System Errors:      0

📈 By Category:
  Basic Queries: 6/6 (100.0%)
  Health & Status: 5/5 (100.0%)
  SSL Certificate Management: 4/5 (80.0%)
  ...

📄 Detailed report saved: testing/evaluations/query_evaluation_report.html
```

### Single Query Output

```
🔍 Testing query: Show me all load balancers
============================================================
✅ SUCCESS
```

Or on failure:

```
🔍 Testing query: Show nonexistent table
============================================================
❌ SCHEMA_FAIL
🔍 Schema analysis error: Table 'nonexistent' not found in database
```

## HTML Report

The generated HTML report includes:

- **Summary Metrics**: Success rate, charts generated
- **Results by Category**: Breakdown by query type
- **Detailed Results Table**: All queries with:
  - Query text
  - Category
  - Row count returned
  - Chart type (if generated)
  - Execution time
  - Status (color-coded)

Open in browser:
```bash
open testing/evaluations/query_evaluation_report.html
```

## Integration with Development

### Pre-commit Hooks

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
python testing/evaluate_queries.py
if [ $? -ne 0 ]; then
    echo "❌ Query evaluation failed"
    exit 1
fi
```

### CI/CD Pipeline

GitHub Actions example:
```yaml
- name: Run Query Evaluation
  run: |
    python testing/evaluate_queries.py
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
    NETQUERY_ENV: dev
```

### Performance Monitoring

Track metrics over time:
- Success rates by environment
- Query execution times
- Failure pattern analysis
- Chart generation rates
- Category-specific success rates

## Customizing Query Sets

### Adding Queries

Edit the appropriate query set file:

**Dev queries** (`testing/query_sets/dev.json`):
```json
{
  "Your Category": [
    "Your test query here",
    "Another test query"
  ]
}
```

**Prod queries** (`testing/query_sets/prod.json`):
```json
{
  "Wide IP & Global Load Balancing": [
    "Show all wide IPs",
    "List wide IP pool members"
  ]
}
```

### Query Set Format

```json
{
  "Category Name": [
    "Query 1",
    "Query 2",
    "Query 3"
  ],
  "Another Category": [
    "Query A",
    "Query B"
  ]
}
```

### Best Practices

1. **Environment-Specific**: Don't query tables that don't exist in that environment
   - Dev: Has `ssl_certificates`, `network_connectivity` tables
   - Prod: Has `wide_ips`, `wide_ip_pools`, `traffic_stats` tables

2. **Include Edge Cases**: Test error handling
   - Invalid table names
   - Missing data
   - Unsafe operations (should be blocked)

3. **Cover Complexity Levels**: From simple to advanced
   - Basic: Single table SELECT
   - Medium: JOINs, aggregations
   - Advanced: Subqueries, window functions, CTEs

4. **Realistic Queries**: Based on actual use cases
   - Operational monitoring
   - Troubleshooting scenarios
   - Reporting and analytics

## Files and Locations

- **Evaluation Script**: `testing/evaluate_queries.py`
- **Dev Query Set**: `testing/query_sets/dev.json`
- **Prod Query Set**: `testing/query_sets/prod.json`
- **Reports Directory**: `testing/evaluations/`
- **Configuration**: `.env` for API keys and database URLs

## Troubleshooting

### "GEMINI_API_KEY not set" error
```bash
export GEMINI_API_KEY="your-api-key"
# or add to .env file
```

### Database connection errors
Ensure database is set up:
```bash
# Dev mode
./start-dev.sh

# Prod mode
./start-prod.sh
```

### Import errors
Use the virtual environment:
```bash
source .venv/bin/activate
```

### Query set not found
Check file exists:
```bash
ls testing/query_sets/
# Should show: dev.json  prod.json
```

## Future Improvements

### Technical Success Rate Enhancements

**Adaptive Model Selection**
- Use advanced models (gemini-2.5-pro) for high-complexity queries
- Use standard models (gemini-2.0-flash) for simple queries
- Optimize cost vs. performance trade-off

**Schema Analysis Enhancement**
- Upgrade embedding model from `all-MiniLM-L6-v2` to `text-embedding-3-large`
- Add hybrid search (semantic + BM25 lexical matching)
- Enhance table descriptions with domain-specific keywords

**SQL Generation Resilience**
- SQL validation with retry and increased reasoning
- Few-shot learning with domain-specific examples
- Automatic query optimization (LIMIT clauses, execution controls)

### Error Recovery

**Smart Recovery Patterns**
- Query decomposition for complex requests
- Intelligent fallback to simpler variants
- Better error messages with suggested alternatives

**Learning System**
- Track success patterns by query complexity
- Log failures for pattern analysis
- Adaptive difficulty scoring based on history

### Measurement Enhancements

**Additional Metrics**
- Success rate by complexity level (simple/medium/advanced)
- Average execution time by category
- Schema analysis accuracy by table type
- Failure mode distribution and trends
- Chart generation success rate

**Reporting Enhancements**
- Trend analysis over multiple runs
- Comparison between dev and prod success rates
- Performance regression detection
- Query recommendation based on successful patterns

## Summary

The evaluation framework ensures Netquery maintains high quality and reliability across:
- Multiple environments (dev SQLite, prod PostgreSQL)
- Diverse query types (basic to advanced SQL)
- Different complexity levels
- Edge cases and error scenarios
- Visualization generation capabilities

For more details, see:
- [Testing README](../testing/README.md) - Complete testing guide
- [Sample Queries](SAMPLE_QUERIES.md) - Example queries for manual testing
- [Getting Started](GETTING_STARTED.md) - Setup and usage guide
