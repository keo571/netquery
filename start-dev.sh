#!/bin/bash
# Start Netquery in DEV mode (SQLite)
# Fast, simple, no Docker needed

set -e

echo "🚀 Starting Netquery - DEV MODE (SQLite)"
echo "========================================="
echo ""

# Switch to dev profile and initialize
./profile.sh dev init

echo ""
echo "✅ Dev mode ready!"
echo ""
echo "📝 Try a query:"
echo '   python gemini_cli.py "Show me all load balancers"'
echo ""
echo "💡 Optional - Start API server:"
echo "   ./api-server.sh"
echo ""
