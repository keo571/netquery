#!/bin/bash
# Database Configuration Switcher
# Usage: ./scripts/switch_database.sh [sqlite|postgres]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

show_usage() {
    echo "Usage: $0 [sqlite|postgres]"
    echo ""
    echo "Switch between SQLite and PostgreSQL database configurations"
    echo ""
    echo "Options:"
    echo "  sqlite    - Switch to SQLite (file-based, simple)"
    echo "  postgres  - Switch to PostgreSQL (Docker-based, production-like)"
    echo ""
    echo "Examples:"
    echo "  $0 sqlite"
    echo "  $0 postgres"
}

show_current_config() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${BLUE}Current configuration:${NC}"
        grep "^DATABASE_URL=" "$PROJECT_ROOT/.env" || echo "  No DATABASE_URL found"
    else
        echo -e "${YELLOW}No .env file found${NC}"
    fi
}

switch_to_sqlite() {
    echo -e "${GREEN}Switching to SQLite...${NC}"

    if [ ! -f "$PROJECT_ROOT/.env.dev" ]; then
        echo -e "${RED}Error: .env.dev not found${NC}"
        exit 1
    fi

    # Preserve GEMINI_API_KEY if it exists
    if [ -f "$PROJECT_ROOT/.env" ] && grep -q "^GEMINI_API_KEY=" "$PROJECT_ROOT/.env"; then
        API_KEY=$(grep "^GEMINI_API_KEY=" "$PROJECT_ROOT/.env" | head -1)
    fi

    cp "$PROJECT_ROOT/.env.dev" "$PROJECT_ROOT/.env"

    # Restore API key if it was found
    if [ ! -z "$API_KEY" ] && [ "$API_KEY" != "GEMINI_API_KEY=your_gemini_api_key_here" ]; then
        sed -i.bak "s|^GEMINI_API_KEY=.*|$API_KEY|" "$PROJECT_ROOT/.env"
        rm "$PROJECT_ROOT/.env.bak"
    fi

    echo -e "${GREEN}✅ Switched to SQLite${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Create sample data:  python scripts/create_data_sqlite.py"
    echo "  2. Run queries:         python gemini_cli.py \"Show me all servers\""
}

switch_to_postgres() {
    echo -e "${GREEN}Switching to PostgreSQL...${NC}"

    if [ ! -f "$PROJECT_ROOT/.env.prod" ]; then
        echo -e "${RED}Error: .env.prod not found${NC}"
        exit 1
    fi

    # Check if Docker is running
    if ! docker ps > /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Docker is not running${NC}"
        echo "Start Docker Desktop before using PostgreSQL"
    fi

    # Check if postgres container is running
    if ! docker ps | grep -q "netquery-postgres"; then
        echo -e "${YELLOW}Warning: PostgreSQL container is not running${NC}"
        echo "Start it with: docker-compose up -d"
    fi

    # Preserve GEMINI_API_KEY if it exists
    if [ -f "$PROJECT_ROOT/.env" ] && grep -q "^GEMINI_API_KEY=" "$PROJECT_ROOT/.env"; then
        API_KEY=$(grep "^GEMINI_API_KEY=" "$PROJECT_ROOT/.env" | head -1)
    fi

    cp "$PROJECT_ROOT/.env.prod" "$PROJECT_ROOT/.env"

    # Restore API key if it was found
    if [ ! -z "$API_KEY" ] && [ "$API_KEY" != "GEMINI_API_KEY=your_gemini_api_key_here" ]; then
        sed -i.bak "s|^GEMINI_API_KEY=.*|$API_KEY|" "$PROJECT_ROOT/.env"
        rm "$PROJECT_ROOT/.env.bak"
    fi

    echo -e "${GREEN}✅ Switched to PostgreSQL${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Ensure DB is running: docker-compose up -d"
    echo "  2. Create sample data:   python scripts/create_data_postgres.py"
    echo "  3. Run queries:          python gemini_cli.py \"Show me all servers\""
    echo "  4. View in pgAdmin:      http://localhost:5050"
}

# Main script
case "${1:-}" in
    sqlite)
        switch_to_sqlite
        ;;
    postgres|postgresql)
        switch_to_postgres
        ;;
    "")
        show_current_config
        echo ""
        show_usage
        exit 1
        ;;
    *)
        echo -e "${RED}Error: Invalid option '$1'${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac

echo ""
show_current_config
