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
│   └── dev.json           # Sample database queries (80+ test queries)
├── evaluations/            # Generated evaluation reports (created on run, gitignored)
├── table_exports/          # Exported database tables (created on run, gitignored)
├── export_database_tables.py # Export all database tables to CSV
└── evaluate_queries.py     # Comprehensive query evaluation framework
```

## Quick Start

### Export Database Tables

Export all tables from the sample database to CSV files:

```bash
python testing/export_database_tables.py
```

Output: CSV files in `testing/table_exports/` (auto-created)

### Evaluate Queries

Run comprehensive query evaluation with HTML reports:

```bash
# Evaluate all queries in the sample database
python testing/evaluate_queries.py

# Test a single query (quick pass/fail)
python testing/evaluate_queries.py --single "Show all load balancers"
```

Output: HTML report at `testing/evaluations/query_evaluation_report.html`

### Test API Endpoints

Test the FastAPI server (requires server running on http://localhost:8000):

```bash
# Start the API server first
SCHEMA_ID=sample python -m src.api.server --port 8000

# In another terminal, run tests
python testing/api_tests/test_api.py
python testing/api_tests/test_no_execute.py
python testing/api_tests/test_large_query.py
python testing/api_tests/test_llm_interpretation.py
```

## Query Sets

### Sample Database (`query_sets/dev.json`)

Tests for the sample SQLite database with the following tables:
- `load_balancers` - Load balancer instances
- `servers` - Backend servers with CPU/memory metrics
- `ssl_certificates` - SSL certificate management
- `vip_pools` - Virtual IP pools
- `backends` - LB to server mappings
- `network_traffic` - Traffic metrics
- `network_connectivity` - Server connectivity metrics

**Query Categories** (15 categories, 80+ queries):
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

See [docs/EVALUATION.md](../docs/EVALUATION.md) for detailed information.

## Evaluation Metrics

The `evaluate_queries.py` script tracks:

- **Success Rate**: Percentage of queries successfully executed
- **Failure Breakdown**:
  - Schema failures (table/column not found)
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

To add queries to the evaluation set:

1. Edit `query_sets/dev.json`

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

1. **Sample database schema**: Only query tables that exist in the sample database
2. **Test edge cases**: Include queries that should fail gracefully
3. **Cover all SQL patterns**: Basic selects, joins, aggregations, subqueries, etc.
4. **Use realistic queries**: Base queries on actual use cases
5. **Document expected behavior**: Especially for edge cases

## Troubleshooting

### "GEMINI_API_KEY not set" error
Set your API key in `.env`:
```bash
GEMINI_API_KEY=your_api_key_here
```

### Database connection errors
Ensure the sample database is set up:
```bash
./setup-cli.sh
```

### API tests fail with connection refused
Start the API server first:
```bash
SCHEMA_ID=sample python -m src.api.server --port 8000
```

### Import errors
Make sure you're using the virtual environment:
```bash
source .venv/bin/activate
```

## Output Directories

These directories are created automatically when running tests:

- `evaluations/` - HTML evaluation reports (gitignored)
- `table_exports/` - Exported CSV files (gitignored)

These are safe to delete and will be regenerated on next run.

## Related Documentation

- [docs/EVALUATION.md](../docs/EVALUATION.md) - Complete evaluation framework guide
- [docs/SAMPLE_QUERIES.md](../docs/SAMPLE_QUERIES.md) - Example queries for manual testing
- [docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md) - Setup and usage guide
