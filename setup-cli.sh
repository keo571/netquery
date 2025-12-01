#!/bin/bash
# Setup CLI Environment
# Prepares environment and sample database for CLI usage (gemini_cli.py)

set -e

echo "🚀 Setting up CLI Environment"
echo "=============================="
echo ""

# Check if .env.sample exists
if [ ! -f ".env.sample" ]; then
    echo "❌ Error: .env.sample not found"
    echo "Please ensure .env.sample exists in the project root"
    exit 1
fi

# Check if API key is configured
api_key=$(grep "^GEMINI_API_KEY=" .env.sample 2>/dev/null | cut -d'=' -f2- | tr -d ' ' || echo "")
if [ -z "$api_key" ] || [ "$api_key" = "your_gemini_api_key_here" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY not configured in .env.sample"
    echo "Please edit .env.sample and add your API key"
    echo ""
fi

echo "✓ Using .env.sample configuration"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠️  Warning: No virtual environment found at .venv"
    echo "Consider creating one with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    echo ""
fi
echo ""

# Check if sample database exists
if [ ! -f "data/sample.db" ]; then
    echo "📦 Creating sample database..."
    python scripts/create_sample_data.py
    echo "✓ Sample database created"
    echo ""
fi

# Check if schema embeddings exist
if [ ! -f "data/sample_embeddings_cache.db" ]; then
    echo "🔨 Building schema embeddings..."
    python -m src.schema_ingestion build \
        --schema-id sample \
        --excel-path schema_files/sample_schema.xlsx \
        --output-path schema_files/sample_schema.json
    echo "✓ Schema embeddings created"
    echo ""
fi

echo ""
echo "✅ CLI environment ready!"
echo ""
echo "📝 Try a CLI query:"
echo '   python gemini_cli.py "Show me all load balancers"'
echo ""
echo "💡 For frontend/API usage, use dual backends instead:"
echo "   ./start-dual-backends.sh"
echo ""
