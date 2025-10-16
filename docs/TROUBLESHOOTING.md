# Troubleshooting Guide

Quick solutions to common issues.

---

## Query Issues

### "I couldn't find relevant database tables"

**Cause:** Schema analyzer couldn't match your query to tables

**Solutions:**
1. Check your tables exist: `python gemini_cli.py "list all tables"`
2. Rebuild embeddings: `python -m src.schema_ingestion build --output schema_files/dev_schema.json`
3. Use specific table names: "Show me data from **servers** table"
4. Lower similarity threshold in `.env`: `RELEVANCE_THRESHOLD=0.10`

---

### "Database query timed out after 45 seconds"

**Cause:** Query too slow or database locked

**Solutions:**
1. Check query complexity: Look at the generated SQL in output
2. For SQLite: Only one write at a time (close other connections)
3. For PostgreSQL: Check `docker ps` to ensure it's running
4. Simplify query: Break into smaller questions

---

### "Validation failed: Query contains blocked keyword DELETE"

**Cause:** Safety validator caught destructive operation

**This is intentional!** Netquery is read-only by design.

If you really need to modify data, use direct SQL:
```bash
sqlite3 data/infrastructure.db "UPDATE servers SET status='active'"
```

---

## Setup Issues

### "GEMINI_API_KEY environment variable not set"

**Solutions:**
1. Copy template: `cp .env.dev .env`
2. Edit `.env` and add your key from [Google AI Studio](https://aistudio.google.com/)
3. Verify: `grep GEMINI_API_KEY .env` should show your key

---

### "No module named 'sqlalchemy'"

**Cause:** Dependencies not installed

**Solution:**
```bash
pip install -r requirements.txt
# Or use virtual environment:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

### PostgreSQL: "Connection refused on port 5432"

**Cause:** PostgreSQL not running

**Solution:**
```bash
# Check if running
docker ps | grep postgres

# If not running, start it
./profile.sh prod init

# Or manually start your database (examples)
# docker compose up -d postgres   # if you maintain a compose file
# brew services start postgresql  # macOS/Homebrew
# sudo systemctl start postgresql # Linux distros
```

---

## Performance Issues

### First query slow (~5 seconds), subsequent queries fast

**This is normal!** First query loads:
- Database schema (~1s)
- Embedding model (~2s)
- Establishes connections (~1s)

Subsequent queries reuse these and complete in <1 second.

---

### Embeddings cache taking up disk space

**Location:** `.embeddings_cache/` directory

**Safe to delete?** Yes, they'll be regenerated on next query (takes ~30s)

**To rebuild:**
```bash
rm -rf .embeddings_cache/
python gemini_cli.py "show all tables"  # Rebuilds cache
```

---

## Development Issues

### "ModuleNotFoundError: No module named 'src'"

**Cause:** Python can't find the `src/` directory

**Solution:**
```bash
# Run from project root, not from subdirectories
cd /path/to/netquery
python gemini_cli.py "query"

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

### Changes to code not taking effect

**For CLI:** Just run again (no restart needed)

**For API server:** Restart the server:
```bash
# Kill existing
pkill -f "uvicorn"

# Restart
./dev-start.sh
```

---

## Getting Help

### Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python gemini_cli.py "your query"
```

This shows:
- Which tables were selected
- Generated SQL
- Validation steps
- Execution time

### Check System Status

```bash
# Database connection
./profile.sh status

# API server (if running)
curl http://localhost:8000/health
```

### Common Fixes

```bash
# Nuclear option: Reset everything
rm -rf .embeddings_cache/
rm data/*.db
./profile.sh dev init
```

---

## Still Stuck?

1. Check [docs/SAMPLE_QUERIES.md](SAMPLE_QUERIES.md) for examples
2. Try simpler queries first: "show all tables", "count servers"
3. Check logs in console output for error details
4. File an issue on GitHub with:
   - Your query
   - Error message
   - Output of `./profile.sh status`
