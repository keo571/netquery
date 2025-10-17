#!/usr/bin/env python3
"""
Export all database tables to CSV files.
Useful for data analysis, backup, or sharing sample data.

NOTE: This script only works with SQLite databases (dev mode).
For PostgreSQL, use standard pg_dump or pgAdmin export tools.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.common.env import load_environment
from src.text_to_sql.tools.database_toolkit import db_toolkit
import pandas as pd

def export_all_tables():
    """Export all database tables to CSV files (SQLite only)."""
    # Load environment to check database type
    load_environment()

    # Check if using SQLite
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("sqlite"):
        print("❌ Error: This script only works with SQLite databases (dev mode)")
        print(f"   Current DATABASE_URL: {database_url}")
        print("\n💡 Solutions:")
        print("   1. Switch to dev mode: ./start-dev.sh")
        print("   2. For PostgreSQL, use: docker compose exec postgres pg_dump ...")
        print("   3. Or use pgAdmin web interface: http://localhost:5050")
        return False

    # Create testing/table_exports directory for database table exports
    export_dir = Path(__file__).parent.parent / "testing" / "table_exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    env_mode = os.getenv("NETQUERY_ENV", "dev")
    print(f"🚀 Starting database table export (SQLite - {env_mode} mode)...")
    print(f"📁 Export directory: {export_dir.absolute()}")
    
    # Get all table names
    table_names = db_toolkit.get_table_names()
    
    if not table_names:
        print("❌ No tables found in database")
        return
    
    print(f"📊 Found {len(table_names)} tables: {', '.join(table_names)}")
    print("=" * 60)
    
    exported_count = 0
    total_rows = 0
    
    for table_name in table_names:
        try:
            print(f"📤 Exporting {table_name}...", end=" ")
            
            # Get all data from table
            query = f"SELECT * FROM {table_name}"
            result = db_toolkit.execute_query(query)
            
            if result.get("success", False) and result.get("data"):
                data = result["data"]
                row_count = len(data)
                
                # Save to CSV
                csv_path = export_dir / f"{table_name}.csv"
                pd.DataFrame(data).to_csv(csv_path, index=False)
                
                print(f"✅ {row_count} rows → {csv_path.name}")
                exported_count += 1
                total_rows += row_count
                
            else:
                print(f"❌ No data or error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error exporting {table_name}: {e}")
    
    print("=" * 60)
    print(f"✅ Export complete!")
    print(f"📊 Summary: {exported_count}/{len(table_names)} tables exported")
    print(f"📈 Total rows: {total_rows:,}")
    print(f"📁 Location: {export_dir.absolute()}")

    if exported_count > 0:
        print(f"\n💡 Tip: Use these CSV files for data analysis or sharing sample data")

    return True

def main():
    """Main function."""
    try:
        result = export_all_tables()
        return 0 if result else 1
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())