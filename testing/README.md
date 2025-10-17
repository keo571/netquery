# Testing Directory

This directory contains test scripts and evaluation tools for the Netquery text-to-SQL pipeline.

## Directory Structure

```
testing/
├── api_tests/              # FastAPI endpoint tests
│   ├── test_api.py        # General API endpoint testing
│   ├── test_no_execute.py # Test SQL generation without execution
│   ├── test_large_query.py # Test performance with large result sets
│   └── test_llm_interpretation.py # Test LLM-powered interpretation
├── query_sets/             # Evaluation query sets
│   ├── dev.json           # SQLite (dev) mode queries
│   └── prod.json          # PostgreSQL (prod) mode queries
├── evaluations/            # Generated evaluation reports (created on run)
├── table_exports/          # Exported database tables (created on run)
├── export_database_tables.py # Export all database tables to CSV
└── evaluate_queries.py     # Comprehensive query evaluation framework
```

## Quick Start

### Export Database Tables

Export all tables from SQLite database to CSV files:

```bash
# Export dev database tables (SQLite only)
python testing/export_database_tables.py
```

**Note**: This script only works with SQLite (dev mode). For PostgreSQL exports:
```bash
# PostgreSQL export options
docker compose exec postgres pg_dump -U netquery netquery > backup.sql
# Or use pgAdmin web interface at http://localhost:5050
```

Output: CSV files in `testing/table_exports/`

### Evaluate Queries

Run comprehensive query evaluation with HTML reports:

```bash
# Evaluate all dev queries
python testing/evaluate_queries.py

# Evaluate all prod queries
NETQUERY_ENV=prod python testing/evaluate_queries.py

# Test a single query (quick pass/fail)
python testing/evaluate_queries.py --single "Show all load balancers"
```

Output: HTML report at `testing/evaluations/query_evaluation_report.html`

### Test API Endpoints

Test the FastAPI server (requires server running on http://localhost:8000):

```bash
# Start the API server first
./api-server.sh

# In another terminal, run tests
python testing/api_tests/test_api.py
python testing/api_tests/test_no_execute.py
python testing/api_tests/test_large_query.py
python testing/api_tests/test_llm_interpretation.py
```

## Query Sets

### Dev Mode (`query_sets/dev.json`)

Tests for SQLite database with the following tables:
- `load_balancers` - Load balancer instances
- `servers` - Backend servers with CPU/memory metrics
- `ssl_certificates` - SSL certificate management
- `vip_pools` - Virtual IP pools
- `backend_mappings` - LB to server mappings
- `network_traffic` - Traffic metrics
- `ssl_monitoring` - SSL monitoring aggregates
- `lb_health_log` - Health scores over time
- `network_connectivity` - Server connectivity metrics

**Query Categories**:
- Basic Queries
- Health & Status
- Aggregations
- Traffic & Performance
- Multi-Table Joins
- SSL Certificate Management
- Network Monitoring
- Time-based Queries
- Comparative & Advanced
- HAVING & Filters
- Existence & NULL Checks
- String Operations
- Conditional Logic
- Complex Analytics
- Edge Cases

### Prod Mode (`query_sets/prod.json`)

Tests for PostgreSQL database with the following tables:
- `load_balancers` - Load balancer instances
- `virtual_ips` - Virtual IP endpoints
- `wide_ips` - Global DNS load balancing
- `wide_ip_pools` - Wide IP pool configurations
- `backend_servers` - Backend server instances
- `traffic_stats` - Per-VIP traffic statistics

**Query Categories**:
- Basic Queries
- Inventory & Filtering
- Status & Health
- Aggregations & Summaries
- Relationship Queries
- Wide IP & Global Load Balancing
- Traffic Analysis
- Multi-Table Joins
- Comparative & Advanced
- HAVING & Aggregation Filters
- Existence & NULL Checks
- String Operations
- Conditional Logic
- Time-based Queries
- Complex Analytics
- Edge Cases

## Evaluation Metrics

The `evaluate_queries.py` script tracks:

- **Success Rate**: Percentage of queries successfully executed
- **Failure Breakdown**:
  - Schema failures (table/column not found)
  - Planning failures (query understanding)
  - Generation failures (SQL generation)
  - Validation failures (SQL validation)
  - Execution failures (database errors)
  - Timeouts (>30 seconds)
  - System errors (exceptions)
- **Chart Generation**: Number of visualizations created
- **Performance**: Execution time per query
- **Category Stats**: Success rate by query category

## API Test Scripts

### test_api.py
General API endpoint testing covering:
- `/api/generate-sql` - SQL generation
- `/api/execute/{query_id}` - Query execution
- `/api/interpret/{query_id}` - Result interpretation
- `/health` - Health check

### test_no_execute.py
Tests the `execute=False` option to generate SQL without running it.

### test_large_query.py
Tests performance optimization with large result sets and row counting limits.

### test_llm_interpretation.py
Tests LLM-powered interpretation service for intelligent insights and visualization suggestions.

## Adding New Test Queries

To add queries to the evaluation sets:

1. Edit the appropriate file:
   - `query_sets/dev.json` for SQLite queries
   - `query_sets/prod.json` for PostgreSQL queries

2. Add queries to an existing category or create a new one:
```json
{
  "Your Category": [
    "Your test query here",
    "Another test query"
  ]
}
```

3. Run evaluation:
```bash
python testing/evaluate_queries.py
```

## Best Practices

1. **Keep queries schema-specific**: Don't query for tables/columns that don't exist in the target database
2. **Test edge cases**: Include queries that should fail gracefully
3. **Cover all SQL patterns**: Basic selects, joins, aggregations, subqueries, etc.
4. **Use realistic queries**: Base queries on actual use cases
5. **Document expected behavior**: Especially for edge cases

## Troubleshooting

### "GEMINI_API_KEY not set" error
Set your API key:
```bash
export GEMINI_API_KEY="your-api-key"
```

### Database connection errors
Ensure the database is set up for your environment:
```bash
# Dev mode
./start-dev.sh

# Prod mode
./start-prod.sh
```

### API tests fail with connection refused
Start the API server first:
```bash
./api-server.sh
```

### Import errors
Make sure you're using the virtual environment:
```bash
source .venv/bin/activate  # or: . .venv/bin/activate
```

## Output Directories

These directories are created automatically when running tests:

- `evaluations/` - HTML evaluation reports
- `table_exports/` - Exported CSV files

These are gitignored and safe to delete.
