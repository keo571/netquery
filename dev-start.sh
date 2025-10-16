#!/bin/bash

# Development startup script for Netquery Backend
# Can be used standalone or called by universal-agent-chat

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
NETQUERY_ENV="${NETQUERY_ENV:-prod}"  # Default to prod, override with NETQUERY_ENV=dev
NETQUERY_PORT="${NETQUERY_PORT:-8000}"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Netquery Backend - Development Startup${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if PostgreSQL is running
echo -e "${BLUE}[1/3] Checking PostgreSQL...${NC}"
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
    echo -e "${YELLOW}  Please start PostgreSQL manually:${NC}"
    echo -e "${YELLOW}    - macOS (Homebrew): brew services start postgresql@16${NC}"
    echo -e "${YELLOW}    - Linux: sudo systemctl start postgresql${NC}"
    echo -e "${YELLOW}    - Or use Postgres.app on macOS${NC}"
    exit 1
else
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
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
echo -e "${BLUE}[3/3] Starting Netquery Backend...${NC}"
echo -e "${YELLOW}  Environment: $NETQUERY_ENV${NC}"
echo -e "${YELLOW}  Port: $NETQUERY_PORT${NC}"
echo ""

NETQUERY_ENV=$NETQUERY_ENV python -m uvicorn src.api.server:app --reload --port $NETQUERY_PORT

# Note: This script blocks here while the server runs
# If you want it to run in background, add & at the end of the uvicorn command
