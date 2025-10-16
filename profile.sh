#!/bin/bash
# Netquery Profile Manager
# One command to switch between dev and prod environments
# Usage: ./profile.sh [dev|prod|init|status]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get project root
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

show_usage() {
    echo "Usage: $0 [dev|prod|init|status]"
    echo ""
    echo "Commands:"
    echo "  dev      - Switch to development profile (SQLite)"
    echo "  prod     - Switch to production profile (PostgreSQL)"
    echo "  init     - Initialize current profile (create data + build schema)"
    echo "  status   - Show current profile and configuration"
    echo ""
    echo "Examples:"
    echo "  $0 dev           # Switch to dev mode"
    echo "  $0 prod init     # Switch to prod and initialize"
    echo "  $0 init          # Initialize current profile"
    echo "  $0 status        # Check what profile you're using"
}

get_current_profile() {
    if [ ! -f ".env" ]; then
        echo "none"
        return
    fi

    local db_url=$(grep "^DATABASE_URL=" .env | head -1 | cut -d'=' -f2)

    if [[ "$db_url" == sqlite* ]]; then
        echo "dev"
    elif [[ "$db_url" == postgresql* ]]; then
        echo "prod"
    else
        echo "unknown"
    fi
}

show_status() {
    local current=$(get_current_profile)

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Netquery Profile Status${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ "$current" == "none" ]; then
        echo -e "${RED}❌ No profile active (.env not found)${NC}"
        echo ""
        echo "Run: $0 dev   or   $0 prod"
        return
    fi

    echo -e "${GREEN}✓ Active Profile: ${YELLOW}$current${NC}"
    echo ""

    if [ -f ".env" ]; then
        echo -e "${BLUE}Configuration:${NC}"
        grep "^DATABASE_URL=" .env | sed 's/^/  /'
        echo ""
    fi

    case "$current" in
        dev)
            echo -e "${BLUE}Details:${NC}"
            echo "  • Database: SQLite (file-based)"
            echo "  • Data script: scripts/create_data_sqlite.py"
            echo "  • Use case: Quick testing, local development"
            ;;
        prod)
            echo -e "${BLUE}Details:${NC}"
            echo "  • Database: PostgreSQL (Docker)"
            echo "  • Data script: scripts/create_data_postgres.py"
            echo "  • Use case: Production-like testing"
            echo ""
            # Check if Docker is running
            if docker ps &> /dev/null; then
                if docker ps | grep -q "netquery-postgres"; then
                    echo -e "  ${GREEN}✓ PostgreSQL container running${NC}"
                else
                    echo -e "  ${YELLOW}⚠ PostgreSQL container not running${NC}"
                    echo "    Start with: docker-compose up -d"
                fi
            else
                echo -e "  ${RED}✗ Docker not running${NC}"
            fi
            ;;
    esac

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

switch_profile() {
    local profile=$1
    local auto_init=$2

    if [ "$profile" != "dev" ] && [ "$profile" != "prod" ]; then
        echo -e "${RED}Error: Invalid profile '$profile'${NC}"
        echo "Use 'dev' or 'prod'"
        exit 1
    fi

    local env_file=".env.$profile"

    if [ ! -f "$env_file" ]; then
        echo -e "${RED}Error: Profile config not found: $env_file${NC}"
        exit 1
    fi

    echo -e "${GREEN}Switching to ${YELLOW}$profile${GREEN} profile...${NC}"
    echo ""

    # Preserve GEMINI_API_KEY if it exists
    local api_key=""
    if [ -f ".env" ] && grep -q "^GEMINI_API_KEY=" .env; then
        api_key=$(grep "^GEMINI_API_KEY=" .env | head -1)
        if [ "$api_key" != "GEMINI_API_KEY=your_gemini_api_key_here" ]; then
            echo -e "${BLUE}  • Preserving your GEMINI_API_KEY${NC}"
        fi
    fi

    # Copy profile config
    cp "$env_file" .env

    # Restore API key
    if [ ! -z "$api_key" ] && [ "$api_key" != "GEMINI_API_KEY=your_gemini_api_key_here" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^GEMINI_API_KEY=.*|$api_key|" .env
        else
            sed -i "s|^GEMINI_API_KEY=.*|$api_key|" .env
        fi
    fi

    echo -e "${GREEN}✓ Switched to $profile profile${NC}"
    echo ""

    # Show what's next
    case "$profile" in
        dev)
            echo -e "${BLUE}Next steps:${NC}"
            echo "  1. Initialize: $0 init"
            echo "  2. Query:      python gemini_cli.py \"Show me all servers\""
            ;;
        prod)
            echo -e "${BLUE}Next steps:${NC}"
            echo "  1. Start DB:   docker-compose up -d"
            echo "  2. Initialize: $0 init"
            echo "  3. Query:      python gemini_cli.py \"Show me all servers\""
            ;;
    esac
    echo ""

    # Auto-initialize if requested
    if [ "$auto_init" == "init" ]; then
        echo -e "${CYAN}Auto-initializing profile...${NC}"
        echo ""
        initialize_profile
    fi
}

initialize_profile() {
    local current=$(get_current_profile)

    if [ "$current" == "none" ]; then
        echo -e "${RED}Error: No profile active${NC}"
        echo "Run: $0 dev   or   $0 prod"
        exit 1
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Initializing ${YELLOW}$current${CYAN} Profile${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    case "$current" in
        dev)
            echo -e "${GREEN}[1/2] Creating SQLite sample data...${NC}"
            if [ -f ".venv/bin/activate" ]; then
                source .venv/bin/activate
            fi
            python scripts/create_data_sqlite.py
            echo ""

            echo -e "${GREEN}[2/2] Building schema...${NC}"
            python scripts/schema_ingest.py build --output schema_files/dev_schema.json
            ;;

        prod)
            # Check if PostgreSQL is running
            if ! docker ps | grep -q "netquery-postgres"; then
                echo -e "${YELLOW}PostgreSQL not running. Starting...${NC}"
                docker-compose up -d postgres
                echo "Waiting for PostgreSQL to be ready..."
                sleep 3
            fi

            echo -e "${GREEN}[1/2] Creating PostgreSQL data from Excel...${NC}"
            if [ -f ".venv/bin/activate" ]; then
                source .venv/bin/activate
            fi
            python scripts/create_data_postgres.py
            echo ""

            echo -e "${GREEN}[2/2] Building schema...${NC}"
            python scripts/schema_ingest.py build --output schema_files/prod_schema.json
            ;;
    esac

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Profile initialized successfully!${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}Ready to query!${NC}"
    echo "  python gemini_cli.py \"Show me all load balancers\""
    echo ""
}

# Main command handler
case "${1:-status}" in
    dev|prod)
        switch_profile "$1" "$2"
        ;;
    init)
        initialize_profile
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$1'${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac
