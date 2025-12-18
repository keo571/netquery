#!/bin/bash

# Start dual backend instances for NetQuery
# This script starts two backend processes:
# - Sample database on port 8000
# - Neila database on port 8001

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
DEV_MODE=false
if [[ "$1" == "--dev" ]]; then
    DEV_MODE=true
fi

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}NetQuery Dual Backend Startup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

if [ "$DEV_MODE" = true ]; then
    echo -e "${YELLOW}Mode: Development (auto-reload enabled, logs visible)${NC}"
else
    echo -e "${YELLOW}Mode: Production (background processes)${NC}"
    echo -e "${YELLOW}Tip: Use --dev flag for development mode with auto-reload${NC}"
fi
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}Warning: No virtual environment found at .venv${NC}"
    echo "Consider creating one with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi
echo ""

# Check if .env.sample exists
if [ ! -f ".env.sample" ]; then
    echo -e "${YELLOW}Warning: .env.sample not found${NC}"
    echo "Please ensure .env.sample exists in the project root"
    exit 1
fi

# Check if .env.neila exists
if [ ! -f ".env.neila" ]; then
    echo -e "${YELLOW}Warning: .env.neila not found${NC}"
    echo "Please create .env.neila configuration file"
    echo "See docs/ADDING_NEW_DATABASE.md for instructions"
    exit 1
fi

# Check if sample database exists
if [ ! -f "data/sample.db" ]; then
    echo -e "${YELLOW}Warning: Sample database not found at data/sample.db${NC}"
    echo "Run: python scripts/create_sample_data.py"
    exit 1
fi

# Check if sample schema exists
if [ ! -f "schema_files/sample_schema.json" ]; then
    echo -e "${YELLOW}Warning: Sample schema not found${NC}"
    echo "Run schema ingestion first:"
    echo "  python -m src.schema_ingestion build --schema-id sample --excel-path schema_files/sample_schema.xlsx --output-path schema_files/sample_schema.json"
    exit 1
fi

# Kill any existing processes on ports 8000 and 8001
echo -e "${GREEN}Checking for existing processes...${NC}"
for port in 8000 8001; do
    PID=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo "  Killing existing process on port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null || true
    fi
done
sleep 1
echo ""

if [ "$DEV_MODE" = true ]; then
    # Development mode: Run in foreground with logs and auto-reload
    echo -e "${GREEN}Starting Sample Database Backend (port 8000) with auto-reload...${NC}"
    echo -e "${YELLOW}Sample logs will appear below:${NC}"
    echo ""

    # Start sample in background with clean environment
    SCHEMA_ID=sample MULTI_DATABASE_MODE=true python3 -m src.api.server --port 8000 --reload &
    SAMPLE_PID=$!

    sleep 2

    # Check if neila database exists
    if [ -f "data/neila.db" ] && [ -f "schema_files/neila_schema.json" ]; then
        echo ""
        echo -e "${GREEN}Starting Neila Database Backend (port 8001) with auto-reload...${NC}"
        echo -e "${YELLOW}Neila logs will appear below:${NC}"
        echo ""

        SCHEMA_ID=neila MULTI_DATABASE_MODE=true python3 -m src.api.server --port 8001 --reload &
        NEILA_PID=$!
    else
        echo -e "${YELLOW}Neila database or schema not found - skipping Neila backend${NC}"
        NEILA_PID=""
    fi

    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${GREEN}Development mode active!${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    echo "Sample: http://localhost:8000 (PID: $SAMPLE_PID)"
    if [ -n "$NEILA_PID" ]; then
        echo "Neila:  http://localhost:8001 (PID: $NEILA_PID)"
    fi
    echo ""
    echo -e "${YELLOW}Auto-reload: Changes to .py files will restart servers${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop all backends${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

else
    # Production mode: Run in background
    echo -e "${GREEN}Starting Sample Database Backend (port 8000)...${NC}"
    SCHEMA_ID=sample MULTI_DATABASE_MODE=true python3 -m src.api.server --port 8000 > /tmp/netquery_sample.log 2>&1 &
    SAMPLE_PID=$!
    echo -e "Sample backend PID: ${SAMPLE_PID}"
    echo -e "Sample logs: /tmp/netquery_sample.log"
    echo ""

    # Wait a moment before starting second backend
    sleep 2

    # Check if neila database and schema exist before starting
    if [ -f "data/neila.db" ] && [ -f "schema_files/neila_schema.json" ]; then
        echo -e "${GREEN}Starting Neila Database Backend (port 8001)...${NC}"
        SCHEMA_ID=neila MULTI_DATABASE_MODE=true python3 -m src.api.server --port 8001 > /tmp/netquery_neila.log 2>&1 &
        NEILA_PID=$!
        echo -e "Neila backend PID: ${NEILA_PID}"
        echo -e "Neila logs: /tmp/netquery_neila.log"
        echo ""
    else
        echo -e "${YELLOW}Neila database or schema not found - skipping Neila backend${NC}"
        echo "To add Neila database, see: docs/ADDING_NEW_DATABASE.md"
        echo ""
        NEILA_PID=""
    fi

    echo -e "${BLUE}================================${NC}"
    echo -e "${GREEN}Backends started successfully!${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    echo "Sample Database API: http://localhost:8000"
    if [ -n "$NEILA_PID" ]; then
        echo "Neila Database API:  http://localhost:8001"
    fi
    echo ""
    echo "API Documentation:"
    echo "  - Sample: http://localhost:8000/docs"
    if [ -n "$NEILA_PID" ]; then
        echo "  - Neila:  http://localhost:8001/docs"
    fi
    echo ""
    echo "Logs:"
    echo "  - Sample: tail -f /tmp/netquery_sample.log"
    if [ -n "$NEILA_PID" ]; then
        echo "  - Neila:  tail -f /tmp/netquery_neila.log"
    fi
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all backends${NC}"
    echo ""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping backends...${NC}"
    kill $SAMPLE_PID 2>/dev/null || true
    if [ -n "$NEILA_PID" ]; then
        kill $NEILA_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}All backends stopped${NC}"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup INT TERM

# Wait for processes
if [ -n "$NEILA_PID" ]; then
    wait $SAMPLE_PID $NEILA_PID
else
    wait $SAMPLE_PID
fi
