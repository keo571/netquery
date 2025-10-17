#!/bin/bash
# Start Netquery in PROD mode (PostgreSQL in Docker)
# Production-like testing with real database

set -e

echo "🚀 Starting Netquery - PROD MODE (PostgreSQL)"
echo "=============================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

# Start PostgreSQL
echo "📦 Starting PostgreSQL container..."
docker compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U netquery > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Check if database has tables
TABLE_COUNT=$(docker compose exec -T postgres psql -U netquery -d netquery -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" = "0" ]; then
    echo ""
    echo "📊 Database is empty. Creating sample data..."
    python setup/create_data_postgres.py
    echo "✅ Sample data created!"
else
    echo "✅ Database already has $TABLE_COUNT tables"
fi

# Switch to prod profile
echo ""
echo "🔄 Switching to production profile..."
./profile.sh prod

echo ""
echo "✅ Prod mode ready!"
echo ""
echo "📝 Try a query:"
echo '   python gemini_cli.py "Show me all load balancers"'
echo ""
echo "💡 Optional - Start API server:"
echo "   ./api-server.sh"
echo ""
echo "🐘 PostgreSQL commands:"
echo "   • View logs:  docker compose logs -f postgres"
echo "   • Stop:       docker compose down"
echo "   • psql shell: docker compose exec postgres psql -U netquery -d netquery"
echo ""
