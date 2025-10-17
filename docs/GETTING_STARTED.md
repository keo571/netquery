# Netquery Startup & Profiles Guide

Quick reference for starting Netquery and managing dev/prod environments.

## Quick Start

**New to Netquery?** Use these scripts:

```bash
# Dev mode (SQLite - fast, simple)
./start-dev.sh
python gemini_cli.py "Show me all load balancers"

# Prod mode (PostgreSQL - production-like)
./start-prod.sh
python gemini_cli.py "Show me all load balancers"
```

That's it! Everything else is automatic.

---

## Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `./start-dev.sh` | **Start DEV mode** | First time, quick testing, local development |
| `./start-prod.sh` | **Start PROD mode** | Production testing, PostgreSQL, Docker |
| `./api-server.sh` | Start API server | When frontend needs REST API |
| `./profile.sh status` | Check current mode | To see if you're in dev or prod |
| `./profile.sh [dev\|prod]` | Switch modes manually | Advanced users |

---

## Two Profiles

| Profile | Database | Data Script | Use Case |
|---------|----------|-------------|----------|
| **dev** | SQLite (file) | `setup/create_data_sqlite.py` | Quick testing, local development |
| **prod** | PostgreSQL (Docker) | `setup/create_data_postgres.py` | Production-like testing |

---

## Manual Profile Management

### Check Current Profile
```bash
./profile.sh status
```

### Switch Profiles
```bash
# Switch to dev (SQLite)
./profile.sh dev

# Switch to prod (PostgreSQL)
./profile.sh prod
```

### Initialize Profile (Create Data + Build Schema)
```bash
# Initialize current profile
./profile.sh init

# Or switch and initialize in one command
./profile.sh dev init
./profile.sh prod init
```

## Typical Workflows

### Option 1: Use Start Scripts (Easiest)
```bash
# Dev mode
./start-dev.sh
python gemini_cli.py "your question"

# Prod mode
./start-prod.sh
python gemini_cli.py "your question"
```

### Option 2: Manual Control
```bash
# Check what you're using
./profile.sh status

# Switch modes
./profile.sh dev    # or: ./profile.sh prod

# Initialize
./profile.sh init

# Query
python gemini_cli.py "your question"
```

## What profile.sh Does

1. **Switches `.env` file** - Copies `.env.dev` or `.env.prod` to `.env`
2. **Preserves your API key** - Your `GEMINI_API_KEY` is kept when switching
3. **Initializes data** - Creates sample data in the right database
4. **Builds schema** - Runs schema ingestion for embeddings

## Config Files

- `.env.dev` - Template for dev (SQLite)
- `.env.prod` - Template for prod (PostgreSQL)
- `.env` - Active config (gitignored, created by profile.sh)

## Advanced: Manual Commands

If you need fine-grained control:

```bash
# Manual database switching (without data creation)
./setup/switch_database.sh sqlite
./setup/switch_database.sh postgres

# Manual data creation
python setup/create_data_sqlite.py
python setup/create_data_postgres.py

# Manual schema building
python -m src.schema_ingestion build --output schema_files/dev_schema.json

# Build with Excel descriptions
python -m src.schema_ingestion build \
  --excel schema_files/load_balancer_schema.xlsx \
  --output schema_files/prod_schema.json
```

## Common Commands

### Starting Netquery
```bash
./start-dev.sh                    # Dev mode
./start-prod.sh                   # Prod mode
./api-server.sh                   # API server (after starting a mode)
```

### Checking Status
```bash
./profile.sh status               # What mode am I in?
docker compose ps                 # Is PostgreSQL running?
```

### Switching Modes
```bash
./start-dev.sh                    # Switch to dev
./start-prod.sh                   # Switch to prod
```

### PostgreSQL Management (Prod Mode)
```bash
docker compose up -d postgres     # Start PostgreSQL
docker compose logs -f postgres   # View logs
docker compose down               # Stop PostgreSQL
docker compose down -v            # Reset database (deletes data!)
docker compose exec postgres psql -U netquery -d netquery  # psql shell
```

### Resetting Everything
```bash
# Dev mode
rm -rf .embeddings_cache/ data/*.db
./start-dev.sh

# Prod mode
docker compose down -v
./start-prod.sh
```

---

## Tips

- Use `./start-dev.sh` for quick iterations and testing queries
- Use `./start-prod.sh` when testing performance or production scenarios
- Your embeddings are stored locally in `.embeddings_cache/` directory
- Check current mode anytime: `./profile.sh status`
- PostgreSQL pgAdmin UI: `docker compose up -d pgadmin` → http://localhost:5050
  - Login: admin@netquery.local / admin
