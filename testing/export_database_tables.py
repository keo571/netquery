#!/usr/bin/env python3
"""
Export all database tables to CSV files.
Useful for data analysis, backup, or sharing sample data.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.text_to_sql.tools.database_toolkit import db_toolkit
import pandas as pd

def export_all_tables():
    """Export all database tables to CSV files."""
    # Create testing/table_exports directory for database table exports  
    export_dir = Path(__file__).parent.parent / "testing" / "table_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    print("🚀 Starting database table export...")
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

def main():
    """Main function."""
    try:
        export_all_tables()
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())