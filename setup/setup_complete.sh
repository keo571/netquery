#!/bin/bash
# Complete Setup Script for Netquery
# Runs all setup steps in sequence: database creation + schema ingestion + verification

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Netquery Complete Setup Script           ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo ""

# Check for .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file with:"
    echo "  cp .env.example .env"
    echo "  # Add your GEMINI_API_KEY"
    exit 1
fi

# Parse arguments
DB_TYPE="${1:-sqlite}"

if [ "$DB_TYPE" != "sqlite" ] && [ "$DB_TYPE" != "postgres" ]; then
    echo -e "${RED}Usage: $0 [sqlite|postgres]${NC}"
    echo ""
    echo "Examples:"
    echo "  $0 sqlite    # Setup with SQLite (default)"
    echo "  $0 postgres  # Setup with PostgreSQL"
    exit 1
fi

echo -e "${GREEN}→ Database Type: $DB_TYPE${NC}"
echo ""

# Step 1: Create Database
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1/3: Creating Database${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"

if [ "$DB_TYPE" = "sqlite" ]; then
    python "$PROJECT_ROOT/setup/create_data_sqlite.py"
else
    echo -e "${BLUE}Checking PostgreSQL connection (DATABASE_URL)...${NC}"
    python "$PROJECT_ROOT/setup/create_data_postgres.py"
fi

echo -e "${GREEN}✅ Database created${NC}"
echo ""

# Step 2: Ingest Schema and Build Embeddings
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2/3: Ingesting Schema & Building Embeddings${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"

python "$PROJECT_ROOT/setup/ingest_schema.py" build \
    --output "$PROJECT_ROOT/schema_files/dev_schema.json"

echo -e "${GREEN}✅ Schema ingested and embeddings generated${NC}"
echo ""

# Step 3: Verify Setup
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3/3: Verifying Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"

# Test query
echo -e "${YELLOW}Running test query...${NC}"
python "$PROJECT_ROOT/gemini_cli.py" "Show me all servers" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test query successful${NC}"
else
    echo -e "${YELLOW}⚠️  Test query failed (check GEMINI_API_KEY in .env)${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete! 🎉                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}What was created:${NC}"
if [ "$DB_TYPE" = "sqlite" ]; then
    echo "  📁 data/infrastructure.db - Sample SQLite database"
else
    echo "  🐳 PostgreSQL database seeded (see DATABASE_URL in .env)"
fi
echo "  📄 schema_files/dev_schema.json - Canonical schema"
echo "  🧠 .embeddings_cache/default/ - Table embeddings"
echo ""
echo -e "${BLUE}Try these commands:${NC}"
echo '  python gemini_cli.py "Show me all load balancers"'
echo '  python gemini_cli.py "Which servers have high CPU?" --html'
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  • Read README.md for more examples"
echo "  • Check docs/SAMPLE_QUERIES.md for query patterns"
echo "  • Run 'python testing/evaluate_queries.py' to test the pipeline"
echo ""
