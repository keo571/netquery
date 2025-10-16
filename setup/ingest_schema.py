#!/usr/bin/env python3
"""
Convenience wrapper for schema ingestion - keeps setup tools together.

This is a thin wrapper that calls the main schema_ingestion package.
All setup-related commands are available in the setup/ directory.

Usage:
    python setup/ingest_schema.py build --output schema_files/dev.json
    python setup/ingest_schema.py summary schema_files/dev_schema.json -v

Or call the package directly:
    python -m src.schema_ingestion build --output schema_files/dev.json
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.schema_ingestion.__main__ import main

if __name__ == '__main__':
    main()
