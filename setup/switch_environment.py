#!/usr/bin/env python3
"""
Environment switching script for Netquery demos.
Switches between sample data (SQLite) and production data (PostgreSQL with Excel schema).
"""
import sys
import shutil
from pathlib import Path

def switch_environment(mode: str):
    """Switch between sample and production environments."""

    project_root = Path(__file__).parent.parent

    if mode not in ['sample', 'production']:
        print("❌ Invalid mode. Use 'sample' or 'production'")
        sys.exit(1)

    # Environment file mapping
    env_files = {
        'sample': '.env.dev',
        'production': '.env.prod'
    }

    try:
        # Copy environment file
        source_env = project_root / env_files[mode]
        target_env = project_root / '.env'

        if source_env.exists():
            shutil.copy2(source_env, target_env)
            print(f"✅ Switched to {mode} environment")
        else:
            print(f"❌ Environment file not found: {source_env}")
            sys.exit(1)

        # Print configuration summary
        print(f"\n📋 {mode.title()} Environment Active:")
        print("-" * 40)

        if mode == 'sample':
            print("🗄️  Database: SQLite (data/infrastructure.db)")
            print("📊 Tables: Load balancers, servers, network monitoring")
            print("🎯 Use Case: Network infrastructure demo")
            print("📝 Schema: Auto-detected from SQLite or `schema_files/dev_schema.json`")
        else:
            print("🗄️  Database: PostgreSQL (configure in .env)")
            print("📊 Tables: Your Excel-defined tables")
            print("🎯 Use Case: Real production data demo")
            print("📝 Schema: Use canonical JSON via `setup/ingest_schema.py`")

        print(f"\n🔄 Next Steps:")
        if mode == 'sample':
            print("1. (Optional) Refresh demo DB: python setup/create_data_sqlite.py")
            print("2. Start server: python -m uvicorn src.api.server:app --reload")
            print("3. Exercise CLI: python gemini_cli.py \"Show me all load balancers\"")
        else:
            print("1. Build schema JSON: python setup/ingest_schema.py build --output schema_files/prod_schema.json")
            print("2. Start server: python -m uvicorn src.api.server:app --reload")
            print("3. Test pipeline: python gemini_cli.py \"Show me top customers\"")

    except Exception as e:
        print(f"❌ Error switching environment: {e}")
        sys.exit(1)


def show_status():
    """Show current environment status."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'

    print("🔍 Current Environment Status:")
    print("-" * 30)

    if not env_file.exists():
        print("❌ No .env file found. Run switch_environment.py first.")
        return

    # Read current .env
    with open(env_file, 'r') as f:
        content = f.read()

    if 'infrastructure.db' in content:
        print("📍 Mode: SAMPLE (Network Infrastructure)")
        print("🗄️  Database: SQLite")
        print("📊 Tables: load_balancers, servers, network_traffic, etc.")
    elif 'postgresql' in content.lower():
        print("📍 Mode: PRODUCTION (PostgreSQL)")
        print("🗄️  Database: PostgreSQL")
        print("📊 Tables: Your Excel-defined tables")
    else:
        print("❓ Unknown environment configuration")

    print(f"\n📄 Environment file: {env_file}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_status()
    elif len(sys.argv) == 2:
        mode = sys.argv[1].lower()
        if mode in ['status', 'show']:
            show_status()
        else:
            switch_environment(mode)
    else:
        print("Usage:")
        print("  python setup/switch_environment.py              # Show current status")
        print("  python setup/switch_environment.py sample       # Switch to sample data")
        print("  python setup/switch_environment.py production   # Switch to production data")
        print("  python setup/switch_environment.py status       # Show current status")
