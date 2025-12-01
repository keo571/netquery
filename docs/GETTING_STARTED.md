# Netquery Startup Guide

Quick reference for starting Netquery with different databases and modes.

## Quick Start

**New to Netquery?** Use these scripts:

```bash
# Setup CLI environment (if using CLI)
./setup-cli.sh
python gemini_cli.py "Show me all load balancers"

# Or start dual API backends for frontend (recommended)
./start_dual_backends.sh
# Then access: http://localhost:8000 (sample), http://localhost:8001 (neila)
```

That's it! Everything else is automatic.

---

## Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `./setup-cli.sh` | **Setup CLI environment** | CLI testing with gemini_cli.py |
| `./start_dual_backends.sh` | **Start dual API backends** | Frontend with database switching (recommended) |
| `./start_dual_backends.sh --dev` | **Dual backends (dev mode)** | Development: auto-reload + visible logs |

**Development vs Production Mode:**
- **Production** (`./start_dual_backends.sh`): Runs in background, logs to `/tmp/netquery_*.log`
- **Development** (`./start_dual_backends.sh --dev`): Auto-reload on code changes, logs visible in terminal

**Note:** `.env.sample` and `.env.neila` are the main database configurations.

---

## Database Configurations

| Config File | Database | Purpose | Use Case |
|-------------|----------|---------|----------|
| `.env.sample` | Sample (SQLite) | Demo/testing database | CLI queries, quick testing |
| `.env.neila` | Neila (SQLite) | Customer database | Production queries |

---

## Manual Setup (Alternative to Scripts)

If you need fine-grained control:

```bash
# Manual data creation
python scripts/create_sample_data.py

# Manual schema building
python -m src.schema_ingestion build \
  --schema-id sample \
  --excel-path schema_files/sample_schema.xlsx \
  --output-path schema_files/sample_schema.json
```

## Config Files

- `.env.sample` - Sample database configuration (SQLite) - **default**
- `.env.neila` - Neila database configuration (SQLite)

The app automatically loads `.env.sample` by default, or `.env.<schema_id>` when `SCHEMA_ID` is set.

## Common Commands

### Starting Netquery
```bash
./setup-cli.sh                    # Setup CLI environment
./start-dual-backends.sh          # Start dual backends (sample on :8000, neila on :8001)
SCHEMA_ID=sample python -m src.api.server --port 8000  # Manual: single API backend
```

### Checking Status
```bash
echo $SCHEMA_ID                   # What database am I using?
grep "^DATABASE_URL=" .env.sample # Database connection
```

### Switching Databases
```bash
# For CLI usage - set SCHEMA_ID
python gemini_cli.py "query"                    # Uses .env.sample (default)
SCHEMA_ID=neila python gemini_cli.py "query"    # Uses .env.neila

# For API backends - run separate instances
SCHEMA_ID=sample python -m src.api.server --port 8000
SCHEMA_ID=neila python -m src.api.server --port 8001
```

### Resetting Everything
```bash
# Remove all databases and caches
rm -rf data/*.db

# Re-setup CLI environment
./setup-cli.sh
```

---

## Multi-Database Setup (Advanced)

NetQuery supports running multiple databases simultaneously with separate backend instances. This is useful when you have multiple database schemas (e.g., Sample and Neila) and want users to switch between them.

### Quick Start: Dual Backends

```bash
# Start both backends at once
./start_dual_backends.sh
```

This starts:
- **Sample database** on `http://localhost:8000`
- **Neila database** on `http://localhost:8001`

### Manual Setup

```bash
# Terminal 1: Sample database
source .venv/bin/activate
SCHEMA_ID=sample python -m src.api.server --port 8000

# Terminal 2: Neila database
source .venv/bin/activate
SCHEMA_ID=neila python -m src.api.server --port 8001
```

### Frontend Integration

Your frontend can switch databases by changing the backend URL:

```javascript
const selectedDatabase = "sample"; // or "neila"
const backendUrl = selectedDatabase === "sample"
  ? "http://localhost:8000"
  : "http://localhost:8001";

fetch(`${backendUrl}/api/generate-sql`, {
  method: "POST",
  body: JSON.stringify({ query: "How many users?" })
});
```

### Adding New Databases

See [docs/ADDING_NEW_DATABASE.md](ADDING_NEW_DATABASE.md) for complete instructions on adding additional databases.

---

## Tips

- Use `./setup-cli.sh` for CLI testing and quick iterations with `gemini_cli.py`
- Use `./start_dual_backends.sh` for frontend integration with database switching (recommended)
- Your embeddings are stored per-database in `data/{schema_id}_embeddings_cache.db`
- Each database has isolated caches - no cross-contamination
- `.env.sample` and `.env.neila` are your main configs - `.env` is auto-generated
