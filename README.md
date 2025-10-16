# Netquery - Network Infrastructure Text-to-SQL

An AI-powered assistant that converts natural language queries into SQL. Optimized for network infrastructure monitoring with automatic chart generation and comprehensive safety validation.

## Architecture Overview

```mermaid
flowchart TD
    A([Natural Language Query]) --> B[Schema Analysis<br/>Semantic Similarity]
    B --> C[Query Planning<br/>JSON Structure]
    C --> D[SQL Generation<br/>No CTEs]
    D --> E[Safety Validation<br/>Read-Only Check]
    E -->|✅ Pass| F[Query Execution<br/>Timeout Handling]
    E -->|❌ Block| I[Error Response]
    F --> G[Result Interpretation<br/>Chart Generation]
    G --> H([Response with Charts])

    DB[(Database)] -.->|schema reflection<br/>at startup| CACHE
    CACHE[(Embedding Cache)] -.->|table similarity<br/>scoring| B
    LLM[Gemini API] --> C
    LLM --> D
    LLM --> G
    DB --> F

    style A fill:#4FC3F7,color:#000
    style H fill:#81C784,color:#000
    style I fill:#FF8A65,color:#000
    style E fill:#FFB74D,color:#000
    style CACHE fill:#E1BEE7,color:#000
```

## Quick Start

### Prerequisites
- Python 3.9+
- pip
- Gemini API key from Google AI Studio (exported as `GEMINI_API_KEY`)

### Install dependencies
```bash
git clone https://github.com/keo571/netquery.git
cd netquery
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Initialize the development profile (SQLite)
```bash
./profile.sh dev init
python gemini_cli.py "Show me all load balancers"
```
`profile.sh` copies `.env.dev` to `.env`, preserves your API key, seeds the SQLite demo database via `setup/create_data_sqlite.py`, and rebuilds embeddings with `python -m src.schema_ingestion`. Run `./profile.sh status` at any time to check the active profile and database URL.

### Switch to PostgreSQL (optional)
```bash
./profile.sh prod          # Copies .env.prod → .env (edit DATABASE_URL first)
./profile.sh prod init     # Seeds PostgreSQL using setup/create_data_postgres.py
```
Ensure your PostgreSQL instance is running and that `.env` points to it. The init command also writes `schema_files/prod_schema.json` and refreshes embeddings.

### Run the API server
```bash
python -m uvicorn src.api.server:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for interactive OpenAPI documentation.

## Usage Examples

### CLI Interface
```bash
# Basic queries
python gemini_cli.py "Show me all load balancers"
python gemini_cli.py "Which servers have high CPU usage?"

# Analytics with charts
python gemini_cli.py "Show network traffic trends over time" --html
python gemini_cli.py "Display server performance by datacenter" --csv

# Complex multi-table queries
python gemini_cli.py "Show unhealthy load balancers with their backend servers" --explain

# With Excel schema for enhanced metadata
python gemini_cli.py "Show all users" --excel-schema examples/my_schema.xlsx
python gemini_cli.py "Display orders by customer" --excel-schema schema.xlsx --html
```

### FastAPI Server (for Web Applications)
```bash
# Start the server
python -m uvicorn src.api.server:app --reload --port 8000

# Test the endpoints
python -m pytest testing/api_tests/test_api.py                # Full workflow test
python -m pytest testing/api_tests/test_llm_interpretation.py   # LLM interpretation test
python -m pytest testing/api_tests/test_large_query.py          # Large dataset test
```

**API Endpoints:**
- `POST /api/generate-sql` - Convert natural language to SQL
- `GET /api/execute/{query_id}` - Execute SQL and return preview (30 rows)
- `POST /api/interpret/{query_id}` - Get LLM analysis and visualization suggestions
- `GET /api/download/{query_id}` - Download complete results as CSV
- `GET /api/schema/overview` - Discover available tables and suggested starter prompts

### MCP Server (for AI Assistants)
```bash
python -m src.text_to_sql.mcp_server
```

## Optional Integrations

Netquery can plug into additional tooling when you need a richer experience:
- **[netquery-insight-chat](https://github.com/keo571/netquery-insight-chat)** adds a TypeScript/React front end for the text-to-SQL workflow.
- **[netquery-docker](https://github.com/keo571/netquery-docker)** offers a containerized demo environment. It is optional and no longer part of the default quick start.

## Direct Python API
```python
from src.text_to_sql.pipeline.graph import text_to_sql_graph
from langchain_core.messages import HumanMessage

result = await text_to_sql_graph.ainvoke({
    "messages": [HumanMessage(content="Show load balancer health over time")],
    "original_query": "Show load balancer health over time"
})
```

## Query Examples

For comprehensive query examples organized by complexity level, see **[docs/SAMPLE_QUERIES.md](docs/SAMPLE_QUERIES.md)**.

## Configuration

`profile.sh` switches between `.env.dev` (SQLite) and `.env.prod` (PostgreSQL) while keeping your `GEMINI_API_KEY`. The active configuration is always stored in `.env`.

Key variables:

```bash
GEMINI_API_KEY=your_api_key_here          # Required for all LLM calls
DATABASE_URL=sqlite:///data/infrastructure.db  # Overridden when you switch profiles
EXCEL_SCHEMA_PATH=schema_files/load_balancer_schema.xlsx  # Optional metadata source
CANONICAL_SCHEMA_PATH=schema_files/dev_schema.json        # Generated by schema ingestion
SCHEMA_ID=dev                                              # Embedding namespace (defaults to NETQUERY_ENV)
```

See `docs/PROFILES.md` for environment workflows and `docs/TROUBLESHOOTING.md` for common fixes.

## Project Structure

```
├── dev-start.sh                 # Local helper to launch the FastAPI server
├── gemini_cli.py                # Command-line entry point
├── profile.sh                   # Profile manager (dev/prod switching)
├── data/                        # Generated databases (gitignored contents)
│   └── infrastructure.db
├── docs/                        # Architecture notes, guides, troubleshooting
│   ├── PROFILES.md
│   ├── TROUBLESHOOTING.md
│   └── ...
├── outputs/                     # Generated CSV/HTML exports (gitignored contents)
│   ├── query_data/
│   └── query_reports/
├── schema_files/                # Canonical schema JSON + Excel templates
│   ├── dev_schema.json
│   ├── prod_schema.json
│   └── load_balancer_schema.xlsx
├── setup/                       # Data and schema automation
│   ├── create_data_sqlite.py
│   ├── create_data_postgres.py
│   ├── ingest_schema.py
│   ├── setup_complete.sh
│   └── switch_database.sh
├── src/                         # Application code
│   ├── api/
│   ├── common/
│   ├── components/
│   ├── hooks/
│   ├── schema_ingestion/
│   └── text_to_sql/
├── testing/                     # Evaluation tools and fixtures
│   ├── evaluate_queries.py
│   ├── export_database_tables.py
│   ├── api_tests/
│   └── query_sets/
└── requirements.txt             # Python dependencies
```

## Pipeline Architecture

1. **Schema Analysis** → Uses semantic similarity to identify relevant tables from embeddings cache
2. **Query Planning** → Creates structured JSON execution plan with joins, filters, and aggregations
3. **SQL Generation** → Generates optimized SQLite queries (blocks CTEs, uses subqueries)
4. **Safety Validation** → Enforces read-only operations, blocks destructive queries
5. **Query Execution** → Runs SQL with timeout protection and error handling
6. **Result Interpretation** → Generates charts, formats responses, and provides insights

## Development & Testing

```bash
# Smoke test the CLI (generates HTML report in outputs/query_reports/)
python gemini_cli.py "Show server performance by datacenter" --html

# Run the evaluation harness (writes testing/evaluations/query_evaluation_report.html)
python testing/evaluate_queries.py

# Evaluate a single query quickly
python testing/evaluate_queries.py --single "Show all load balancers"

# Export current database tables to CSV for inspection
python testing/export_database_tables.py
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
