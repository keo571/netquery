# Adding a New Database to NetQuery

## Overview

This guide explains how to add a new database to the NetQuery text-to-SQL system. NetQuery supports multiple databases through namespace isolation, allowing you to maintain separate schema definitions, embeddings, and caches for each database environment.

## Prerequisites

- Excel spreadsheet software (for creating schema definition)
- Access to your target database or ability to create sample data
- API key for embedding service (Gemini)
- Python environment with NetQuery dependencies installed

## Directory Structure After Setup

After adding a new database (e.g., `production`), your directory structure will look like:

```
netquery/
├── schema_files/
│   ├── sample_schema.xlsx          # Existing sample database
│   ├── sample_schema.json
│   ├── production_schema.xlsx      # New database Excel
│   └── production_schema.json      # Generated canonical schema
├── data/
│   ├── sample.db                   # Existing sample database
│   ├── sample_embeddings_cache.db
│   ├── sample_sql_cache.db
│   ├── production.db               # New database
│   ├── production_embeddings_cache.db
│   └── production_sql_cache.db
├── scripts/
│   ├── create_sample_data.py       # Existing
│   └── create_production_data.py   # New database creation script
├── .env.sample                      # Existing
├── .env.production                  # New environment config
└── .env                             # Symlink or copy of active env
```

## Step 1: Create Schema Excel File

Create an Excel file at `schema_files/{database}_schema.xlsx` with these sheets:
- **Required**: `table_schema` (table and column definitions)
- **Required**: `mapping` (foreign key relationships)
- **Required**: `suggested_queries` (custom query suggestions for users)

### Sheet 1: `table_schema`

This sheet defines your tables and columns with the following columns:

| Column Name | Required | Description | Example |
|-------------|----------|-------------|---------|
| `table_name` | Yes | Name of the database table | `servers` |
| `column_name` | Yes | Name of the column | `hostname` |
| `data_type` | Yes | SQL data type | `VARCHAR(255)` |
| `description` | Yes | Human-readable description for AI | `Server hostname for identification` |
| `sample_values` | No | Comma-separated example values | `web-01, web-02, db-01` |

**Example rows:**

```
table_name     | column_name   | data_type    | description                           | sample_values
---------------|---------------|--------------|---------------------------------------|---------------------------
servers        | id            | INTEGER      | Primary key for servers table         | 1, 2, 3
servers        | hostname      | VARCHAR(255) | Server hostname for identification    | web-01, web-02, db-01
servers        | datacenter    | VARCHAR(50)  | Datacenter location of server         | us-east-1, us-west-2
servers        | cpu_percent   | REAL         | Current CPU utilization percentage    | 45.2, 78.5, 23.1
load_balancers | id            | INTEGER      | Primary key for load balancers table  | 101, 102, 103
load_balancers | name          | VARCHAR(255) | Load balancer name                    | lb-prod-01, lb-staging
load_balancers | health_score  | INTEGER      | Health score (0-100)                  | 95, 88, 100
```

### Sheet 2: `mapping`

This sheet defines relationships between tables with the following columns:

| Column Name | Required | Description | Example |
|-------------|----------|-------------|---------|
| `table_a` | Yes | First table in relationship | `backends` |
| `column_a` | Yes | Column in first table | `load_balancer_id` |
| `table_b` | Yes | Second table in relationship | `load_balancers` |
| `column_b` | Yes | Column in second table | `id` |

**Example rows:**

```
table_a  | column_a           | table_b        | column_b
---------|--------------------| ---------------|----------
backends | load_balancer_id   | load_balancers | id
backends | server_id          | servers        | id
```

### Sheet 3: `suggested_queries` (Required)

This sheet provides custom query suggestions that users will see in the frontend. **This sheet is required** - at least one query must be provided.

| Column Name | Required | Description | Example |
|-------------|----------|-------------|---------|
| `query` | Yes | Natural language query suggestion | `Show count of servers by datacenter` |

**Best Practices:**

Include queries that support different visualization types:
- **Bar charts**: Count/aggregation queries (e.g., "Show count of servers by datacenter")
- **Pie charts**: Distribution queries (e.g., "Show distribution of load balancers by health status")
- **Line charts**: Time series queries with specific date ranges (e.g., "Show network traffic over the last 30 days")
- **Tables**: List/detail queries (e.g., "Show all unhealthy servers")

**Example rows:**

```
query
------------------------------------------------
Show count of servers by datacenter
Show distribution of load balancers by health status
Show network traffic trend over the last 30 days
List top 10 servers by CPU usage
Show all load balancers with health score below 80
```

**Benefits:**
- Better UX with natural, domain-specific questions
- Visualization-ready queries designed for specific chart types
- Showcases system capabilities to new users
- Helps users understand what questions to ask

### Important Notes:

- Sample values are converted to JSON arrays in the canonical schema
- Descriptions should be clear and contextual to help the AI understand the data
- Use consistent naming conventions across your schema
- Include all foreign key relationships in the mapping sheet
- Add visualization-focused suggested_queries (required - see best practices above)

## Step 2: Run Schema Ingestion

Execute the schema ingestion pipeline to generate the canonical JSON schema and create embeddings:

```bash
python -m src.schema_ingestion build \
  --schema-id production \
  --excel-path schema_files/production_schema.xlsx \
  --output-path schema_files/production_schema.json
```

**Parameters:**
- `--schema-id`: Unique identifier for this database (used for namespace isolation)
- `--excel-path`: Path to your Excel schema file
- `--output-path`: Where to save the canonical JSON schema

**What this does:**
1. Parses the Excel file
2. Generates canonical JSON schema (`production_schema.json`)
3. Creates embeddings for semantic search
4. Stores embeddings in `data/production_embeddings_cache.db`

**Expected output:**
```
Parsing Excel schema...
Generating canonical schema...
Creating embeddings...
Schema ingestion complete!
Canonical schema saved to: schema_files/production_schema.json
Embeddings stored in: data/production_embeddings_cache.db
```

## Step 3: Create Database and Sample Data

Create a script to build your actual database with tables and sample data.

### Option A: SQLite Database

Create `scripts/create_production_data.py`:

```python
import sqlite3
from pathlib import Path

def create_production_database():
    """Create production database with tables and sample data."""

    # Ensure data directory exists
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "production.db"

    # Remove existing database if it exists
    if db_path.exists():
        db_path.unlink()

    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE servers (
            id INTEGER PRIMARY KEY,
            hostname VARCHAR(255) NOT NULL,
            datacenter VARCHAR(50) NOT NULL,
            cpu_percent REAL DEFAULT 0.0,
            memory_percent REAL DEFAULT 0.0,
            status VARCHAR(20) DEFAULT 'active'
        )
    """)

    cursor.execute("""
        CREATE TABLE load_balancers (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            health_score INTEGER DEFAULT 100,
            status VARCHAR(20) DEFAULT 'healthy'
        )
    """)

    cursor.execute("""
        CREATE TABLE backends (
            id INTEGER PRIMARY KEY,
            load_balancer_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            weight INTEGER DEFAULT 1,
            FOREIGN KEY (load_balancer_id) REFERENCES load_balancers(id),
            FOREIGN KEY (server_id) REFERENCES servers(id)
        )
    """)

    # Insert sample data
    cursor.executemany(
        "INSERT INTO servers (id, hostname, datacenter, cpu_percent, memory_percent, status) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "web-01", "us-east-1", 45.2, 62.8, "active"),
            (2, "web-02", "us-east-1", 78.5, 81.3, "active"),
            (3, "db-01", "us-west-2", 23.1, 45.7, "active"),
        ]
    )

    cursor.executemany(
        "INSERT INTO load_balancers (id, name, health_score, status) VALUES (?, ?, ?, ?)",
        [
            (101, "lb-prod-01", 95, "healthy"),
            (102, "lb-staging", 88, "healthy"),
            (103, "lb-prod-02", 100, "healthy"),
        ]
    )

    cursor.executemany(
        "INSERT INTO backends (id, load_balancer_id, server_id, weight) VALUES (?, ?, ?, ?)",
        [
            (1, 101, 1, 10),
            (2, 101, 2, 10),
            (3, 102, 3, 10),
        ]
    )

    conn.commit()
    conn.close()

    print(f"Production database created at: {db_path}")

if __name__ == "__main__":
    create_production_database()
```

Run the script:

```bash
python scripts/create_production_data.py
```

### Option B: PostgreSQL or Other Database

If using PostgreSQL or another database system, modify the script to use the appropriate connection string and SQL dialect. Update your `.env` file with the correct `DATABASE_URL`.

## Step 4: Configure Environment

Create a new environment configuration file `.env.production`:

```bash
# Schema identifier (must match --schema-id from Step 2)
SCHEMA_ID=production

# Database connection
DATABASE_URL=sqlite:///data/production.db

# Canonical schema path
CANONICAL_SCHEMA_PATH=schema_files/production_schema.json

# API keys
GEMINI_API_KEY=your_gemini_api_key_here
```

**Important:**
- The `SCHEMA_ID` must match the `--schema-id` parameter used during schema ingestion for proper namespace isolation.
- Cache file paths are **automatically derived** from `SCHEMA_ID`:
  - Embeddings cache: `data/{SCHEMA_ID}_embeddings_cache.db`
  - SQL cache: `data/{SCHEMA_ID}_sql_cache.db`
- `NETQUERY_ENV` is optional and defaults to `SCHEMA_ID` if not set. You only need it if you want separate environment settings (dev/prod) independent of database selection.

### Switching Between Databases

To switch the active database, update your `.env` file (or create a symlink):

```bash
# Copy the desired environment
cp .env.production .env

# Or create a symlink
ln -sf .env.production .env
```

## Step 5: Verify Setup

### Verify Schema Ingestion

Check that the canonical schema JSON was created:

```bash
cat schema_files/production_schema.json | python -m json.tool | head -20
```

Expected output should show your schema structure with tables, columns, and relationships.

### Verify Embeddings Cache

Check that embeddings were created:

```bash
sqlite3 data/production_embeddings_cache.db "SELECT COUNT(*) FROM embeddings WHERE namespace = 'production';"
```

Expected: A count matching the number of tables + columns in your schema.

### Verify Database

Query your database to confirm tables and data:

```bash
# For SQLite
sqlite3 data/production.db "SELECT name FROM sqlite_master WHERE type='table';"
sqlite3 data/production.db "SELECT * FROM servers LIMIT 3;"
```

Expected: List of your tables and sample data.

### Test Query Pipeline

Start the API server with the new database:

```bash
# Ensure .env points to production
cp .env.production .env

# Start server
python -m src.api.server
```

Send a test query:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many servers are in each datacenter?"}'
```

Expected: SQL query and results based on your production database.

## Example: Adding Production Database

Here's a complete example of adding a production database:

```bash
# 1. Create Excel schema
# Manually create schema_files/production_schema.xlsx with table_schema and mapping sheets

# 2. Run schema ingestion
python -m src.schema_ingestion build \
  --schema-id production \
  --excel-path schema_files/production_schema.xlsx \
  --output-path schema_files/production_schema.json

# 3. Create database
python scripts/create_production_data.py

# 4. Create environment config
cat > .env.production << EOF
SCHEMA_ID=production
DATABASE_URL=sqlite:///data/production.db
CANONICAL_SCHEMA_PATH=schema_files/production_schema.json
GEMINI_API_KEY=your_key_here
EOF

# 5. Switch to production environment
cp .env.production .env

# 6. Verify setup
python -c "from src.common.config import config; print(f'Active schema: {config.schema_id}')"
sqlite3 data/production_embeddings_cache.db "SELECT COUNT(*) FROM embeddings WHERE namespace = 'production';"

# 7. Start server
python -m src.api.server
```

## Namespace Isolation

NetQuery uses namespace isolation to keep databases separate:

- **Schema Embeddings**: Stored in `{database}_embeddings_cache.db` with `namespace` field
- **SQL Cache**: Stored in `{database}_sql_cache.db` (separate file per database)
- **Canonical Schema**: Each database has its own JSON file
- **Environment Config**: Each database has its own `.env` file

This architecture (per ADR-009 and ADR-010) ensures that queries, embeddings, and caches for different databases never interfere with each other.

## Frontend Database Switching

If your frontend (e.g., Code/netquery-insight-chat) allows users to switch between databases, the recommended approach is to run **separate backend instances** for each database.

### Recommended: Separate Backend Instances

Run one backend process per database, each on a different port:

```bash
# Terminal 1: Sample database backend
SCHEMA_ID=sample python -m src.api.server --port 8000

# Terminal 2: Neila database backend
SCHEMA_ID=neila python -m src.api.server --port 8001
```

Or use the environment files:

```bash
# Terminal 1: Sample database
cp .env.sample .env && python -m src.api.server --port 8000

# Terminal 2: Neila database
cp .env.neila .env && python -m src.api.server --port 8001
```

**Frontend Implementation:**

The frontend switches between backend URLs based on user selection:

```javascript
// User clicks database selector
const selectedDatabase = "sample"; // or "neila"

// Determine backend URL
const backendUrl = selectedDatabase === "sample"
  ? "http://localhost:8000"  // Sample backend
  : "http://localhost:8001"; // Neila backend

// Send query to appropriate backend
fetch(`${backendUrl}/query`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: "How many servers are there?"
  })
});
```

**Advantages:**
- ✅ **Simpler backend** - no dynamic switching logic needed
- ✅ **More reliable** - complete isolation between databases
- ✅ **Instant switching** - no AppContext reload delays
- ✅ **Easier debugging** - separate logs per database
- ✅ **Better performance** - no resource contention

### Alternative: Dynamic Schema Switching (Not Recommended)

For reference, you can also implement dynamic switching where the backend accepts a `schema_id` parameter and reloads the AppContext. However, this is **more complex** and has **performance overhead**:

```python
# Frontend sends schema_id with each request
POST /query
{
  "question": "How many users?",
  "schema_id": "neila"
}

# Backend must handle switching
os.environ["SCHEMA_ID"] = request.schema_id
os.environ["DATABASE_URL"] = get_database_url(request.schema_id)
os.environ["CANONICAL_SCHEMA_PATH"] = f"schema_files/{request.schema_id}_schema.json"
AppContext.reset()  # Expensive operation
AppContext.get_instance()  # Reload everything
```

This approach adds complexity and latency. **Use separate backend instances instead.**

### Key Configuration Points

For each database, you need:

1. **Schema ID**: Unique identifier (e.g., `sample`, `neila`)
2. **Environment file**: `.env.{database}` with `SCHEMA_ID`, `DATABASE_URL`, `CANONICAL_SCHEMA_PATH`
3. **Backend port**: Different port for each database (e.g., 8000, 8001)
4. **Frontend mapping**: Map database selection to backend URL

Example `.env.sample`:
```bash
SCHEMA_ID=sample
DATABASE_URL=sqlite:///data/sample.db
CANONICAL_SCHEMA_PATH=schema_files/sample_schema.json
GEMINI_API_KEY=your_key_here
```

Example `.env.neila`:
```bash
SCHEMA_ID=neila
DATABASE_URL=sqlite:///data/neila.db
CANONICAL_SCHEMA_PATH=schema_files/neila_schema.json
GEMINI_API_KEY=your_key_here
```

**Note:** `NETQUERY_ENV` is optional. If not set, it defaults to the `SCHEMA_ID` value. For simple multi-database setups, you only need `SCHEMA_ID`.

## Cache Management

### When to Clean Caches

You need to clean caches in the following scenarios:

1. **Schema Changes (Required)** - When you add/remove tables or columns:
   ```bash
   rm data/{database}_sql_cache.db
   rm data/{database}_embeddings_cache.db
   ```
   Old SQL queries might reference non-existent columns/tables, causing errors.

2. **Data Changes Only (Optional)** - When you only change data (same schema):
   - **SQL Cache**: No need to clean - queries are still valid, will just return new data
   - **Embeddings Cache**: No need to clean - schema structure hasn't changed

### How to Clean Caches

#### Option 1: Delete cache files (simplest)

```bash
# Delete SQL cache only
rm data/production_sql_cache.db

# Delete both caches
rm data/production_sql_cache.db
rm data/production_embeddings_cache.db
```

The backend will automatically recreate these files when it starts.

#### Option 2: Clear via Python API

```python
# Clear SQL cache for a specific database
python3 -c "
from src.text_to_sql.tools.sql_cache import SQLCache

cache = SQLCache(schema_id='production')
cache.clear_all()
print('✓ Production SQL cache cleared')
"
```

#### Option 3: Full reset with embedding rebuild

```bash
# 1. Remove all caches
rm data/production_sql_cache.db
rm data/production_embeddings_cache.db

# 2. Rebuild embeddings (only if you modified the canonical schema JSON)
python3 -c "
from src.schema_ingestion.canonical import CanonicalSchema
from src.schema_ingestion.__main__ import store_embeddings

schema = CanonicalSchema.load('schema_files/production_schema.json')
store_embeddings(schema)
print('✓ Embeddings rebuilt')
"
```

### Quick Clean Script

Create a reusable cleanup script:

```bash
#!/bin/bash
# scripts/clean_cache.sh
DATABASE=${1:-sample}

echo "Cleaning caches for database: $DATABASE"
rm -f data/${DATABASE}_sql_cache.db
rm -f data/${DATABASE}_embeddings_cache.db
echo "✓ Caches cleared for $DATABASE"
echo "Restart the backend to rebuild caches automatically"
```

Usage:
```bash
chmod +x scripts/clean_cache.sh
./scripts/clean_cache.sh production
```

## Troubleshooting

### Schema Ingestion Fails

- Verify Excel file has all 3 required sheets: `table_schema`, `mapping`, and `suggested_queries`
- Check that all required columns are present
- Ensure GEMINI_API_KEY is valid in environment

### Embeddings Cache Empty

- Check that schema ingestion completed successfully
- Verify the `SCHEMA_ID` matches the `--schema-id` parameter
- Review schema ingestion logs for errors

### Queries Return Wrong Data

- Verify `.env` points to correct database environment
- Check `DATABASE_URL` in `.env` file
- Ensure `SCHEMA_ID` matches the ingested schema namespace

### Schema Drift Errors

If you see "Schema drift detected" errors:
- Your database schema doesn't match the canonical schema JSON
- Clean caches and rebuild embeddings after schema changes
- Ensure the canonical schema JSON reflects the actual database structure

### Cache Not Working

- Verify cache database files exist in `data/` directory
- Check file permissions on cache databases
- Review `SQL_CACHE_DB_PATH` and `EMBEDDING_CACHE_DB_PATH` in `.env`
- Try cleaning and rebuilding caches (see Cache Management section above)

## Related Documentation

- [Architecture Decision Records](ARCHITECTURE_DECISION.md) - ADR-009 (SQL Cache), ADR-010 (Embedding Storage)
- [Schema Ingestion Format](../SCHEMA_INGESTION_FORMAT.md) - Detailed canonical schema structure
- [Getting Started Guide](GETTING_STARTED.md) - Initial setup and configuration
