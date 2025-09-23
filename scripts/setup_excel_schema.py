#!/usr/bin/env python3
"""
Setup script to process Excel schema and integrate with Netquery.
Run this script after placing your Excel file in the project.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text_to_sql.tools.excel_schema_parser import ExcelSchemaParser


def setup_excel_schema(excel_file_path: str):
    """Process Excel file and set up schema files."""

    print(f"🔍 Processing Excel schema file: {excel_file_path}")

    try:
        # Parse Excel file
        parser = ExcelSchemaParser(excel_file_path)

        print(f"✅ Found {len(parser.get_table_names())} tables")
        print(f"✅ Found {len(parser.get_relationships())} relationships")

        # Export to table_descriptions.yaml
        descriptions_path = Path(__file__).parent.parent / "src" / "text_to_sql" / "table_descriptions.yaml"
        parser.export_to_yaml(str(descriptions_path))
        print(f"✅ Updated {descriptions_path}")

        # Print summary
        print("\n📊 Schema Summary:")
        print("-" * 40)

        for table_name in parser.get_table_names():
            table_info = parser.get_table_info(table_name)
            columns = [col['name'] for col in table_info['columns']]
            related = parser.get_related_tables(table_name)

            print(f"Table: {table_name}")
            print(f"  Columns: {', '.join(columns)}")
            if related:
                print(f"  Related: {', '.join(related)}")
            print()

        print("🎉 Excel schema setup complete!")
        print("\nNext steps:")
        print("1. Update your environment to point to the Excel file:")
        print(f"   export EXCEL_SCHEMA_PATH='{excel_file_path}'")
        print("2. Restart your Netquery server")
        print("3. Test with queries that use your table names")

    except Exception as e:
        print(f"❌ Error processing Excel file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python setup_excel_schema.py <path_to_excel_file>")
        print("Example: python setup_excel_schema.py /path/to/schema.xlsx")
        sys.exit(1)

    excel_path = sys.argv[1]

    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        sys.exit(1)

    setup_excel_schema(excel_path)