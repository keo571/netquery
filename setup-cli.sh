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

# Copy .env.sample to .env (preserve API key if exists)
if [ -f ".env" ]; then
    # Preserve existing GEMINI_API_KEY
    existing_key=$(grep "^GEMINI_API_KEY=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    cp .env.sample .env
    if [ -n "$existing_key" ] && [ "$existing_key" != "your_gemini_api_key_here" ]; then
        # Use sed to replace the API key line
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$existing_key|" .env
        else
            sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$existing_key|" .env
        fi
        echo "✓ Preserved existing GEMINI_API_KEY"
    fi
else
    cp .env.sample .env
fi

echo "✓ Activated sample database configuration (.env.sample → .env)"
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
echo "   ./start_dual_backends.sh"
echo ""
