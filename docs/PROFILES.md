# Netquery Profiles Guide

Quick reference for managing dev and prod environments.

## Two Profiles

| Profile | Database | Data Script | Use Case |
|---------|----------|-------------|----------|
| **dev** | SQLite (file) | `create_data_sqlite.py` | Quick testing, local development |
| **prod** | PostgreSQL (Docker) | `create_data_postgres.py` | Production-like testing |

## Quick Commands

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

### Query Database
```bash
# After initialization, query away!
python gemini_cli.py "Show me all load balancers"
python gemini_cli.py "What servers are unhealthy?"
```

## Typical Workflows

### Dev Workflow (Quick Testing)
```bash
./profile.sh dev init
python gemini_cli.py "your question"
```

### Prod Workflow (Production Testing)
```bash
# Start PostgreSQL
docker-compose up -d

# Initialize prod
./profile.sh prod init

# Query
python gemini_cli.py "your question"

# When done
docker-compose down
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

## Legacy Scripts

These still work if you prefer manual control:

```bash
# Manual database switching (without data creation)
./scripts/switch_database.sh sqlite
./scripts/switch_database.sh postgres

# Manual data creation
python scripts/create_data_sqlite.py
python scripts/create_data_postgres.py

# Manual schema building
python scripts/schema_ingest.py build --output schema_files/dev_schema.json
```

## Tips

- Use `dev` for quick iterations and testing queries
- Use `prod` when testing performance or production scenarios
- Your embeddings are always stored locally (`.embeddings_cache/`)
- PostgreSQL gives you pgAdmin at http://localhost:5050 (admin@netquery.local / admin)
