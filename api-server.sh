#!/bin/bash

# Netquery FastAPI Server Startup Script
# Starts the backend API server on port 8000
# Uses whatever profile is currently active in .env

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
NETQUERY_PORT="${NETQUERY_PORT:-8000}"

# Detect current profile
if [ -f ".env" ]; then
    DB_URL=$(grep "^DATABASE_URL=" .env | head -1 | cut -d'=' -f2)
    if [[ "$DB_URL" == sqlite* ]]; then
        CURRENT_PROFILE="dev (SQLite)"
    elif [[ "$DB_URL" == postgresql* ]]; then
        CURRENT_PROFILE="prod (PostgreSQL)"
    else
        CURRENT_PROFILE="unknown"
    fi
else
    CURRENT_PROFILE="none - run ./profile.sh dev or ./profile.sh prod"
fi

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Netquery Backend API Server${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Profile: $CURRENT_PROFILE${NC}"
echo ""

# Check database connection based on profile
echo -e "${BLUE}[1/3] Checking database...${NC}"
if [[ "$DB_URL" == postgresql* ]]; then
    if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo -e "${RED}✗ PostgreSQL is not running${NC}"
        echo -e "${YELLOW}  Start PostgreSQL:${NC}"
        echo -e "${YELLOW}    - Docker: docker compose up -d postgres${NC}"
        echo -e "${YELLOW}    - Or run: ./postgres-start.sh${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    fi
elif [[ "$DB_URL" == sqlite* ]]; then
    echo -e "${GREEN}✓ Using SQLite (no server needed)${NC}"
else
    echo -e "${YELLOW}⚠ Unknown database type${NC}"
fi

# Check virtual environment
echo ""
echo -e "${BLUE}[2/3] Checking Python environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}  Creating virtual environment...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${YELLOW}  Installing dependencies...${NC}"
    pip install -r requirements.txt
else
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment ready${NC}"
fi

# Check if port is already in use
if lsof -Pi :$NETQUERY_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}  Port $NETQUERY_PORT already in use. Killing existing process...${NC}"
    lsof -ti:$NETQUERY_PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start backend
echo ""
echo -e "${BLUE}[3/3] Starting Netquery API Server...${NC}"
echo -e "${YELLOW}  Port: $NETQUERY_PORT${NC}"
echo -e "${YELLOW}  API: http://localhost:$NETQUERY_PORT${NC}"
echo ""

python -m uvicorn src.api.server:app --reload --port $NETQUERY_PORT

# Note: This script blocks here while the server runs
# If you want it to run in background, add & at the end of the uvicorn command
