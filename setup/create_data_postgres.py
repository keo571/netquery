#!/usr/bin/env python3
"""
Generate sample production data from Excel schema file.
Creates tables and inserts data based on schema_files/load_balancer_schema.xlsx

Usage:
    python scripts/create_prod_data_from_excel.py
"""
import os
import sys
import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

# Ensure project root on path before importing project modules
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.env import load_environment
from urllib.parse import urlparse

# Load environment
load_environment()

# Fixed paths
EXCEL_FILE = 'schema_files/load_balancer_schema.xlsx'
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://netquery:netquery_dev_password@localhost:5432/netquery')

# Row count range per table
ROW_COUNT_RANGE = (20, 100)


def connect_postgres():
    """Connect to PostgreSQL."""
    parsed = urlparse(DATABASE_URL)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password
    )


def parse_excel_schema():
    """Parse Excel schema file."""
    print(f"📖 Reading Excel schema: {EXCEL_FILE}")

    # Read table_schema sheet
    table_df = pd.read_excel(EXCEL_FILE, sheet_name='table_schema')

    tables = {}
    for table_name, group in table_df.groupby('table_name'):
        columns = []
        for _, row in group.iterrows():
            columns.append({
                'name': row['column_name'],
                'type': row.get('column_type', 'TEXT'),
            })
        tables[table_name] = columns

    print(f"✅ Found {len(tables)} tables: {', '.join(tables.keys())}")
    return tables


def get_sql_type(excel_type):
    """Convert Excel type to PostgreSQL type."""
    type_upper = excel_type.upper()

    if 'INT' in type_upper:
        return 'INTEGER'
    elif 'TEXT' in type_upper or 'VARCHAR' in type_upper or 'CHAR' in type_upper:
        return 'TEXT'
    elif 'DECIMAL' in type_upper or 'REAL' in type_upper or 'FLOAT' in type_upper:
        return 'REAL'
    elif 'TIMESTAMP' in type_upper or 'DATETIME' in type_upper:
        return 'TIMESTAMP'
    elif 'BOOL' in type_upper:
        return 'BOOLEAN'
    elif 'DATE' in type_upper:
        return 'DATE'
    else:
        return 'TEXT'


def create_tables(conn, tables):
    """Create PostgreSQL tables."""
    print("\n🔨 Creating tables...")
    cursor = conn.cursor()

    for table_name, columns in tables.items():
        cols_sql = []
        for i, col in enumerate(columns):
            col_name = col['name']
            col_type = get_sql_type(col['type'])

            # First column with 'id' is primary key
            if i == 0 and 'id' in col_name.lower():
                cols_sql.append(f"{col_name} SERIAL PRIMARY KEY")
            else:
                cols_sql.append(f"{col_name} {col_type}")

        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(cols_sql)})"
        cursor.execute(create_sql)
        print(f"  ✅ {table_name}")

    conn.commit()
    cursor.close()


def generate_sample_data(conn, tables):
    """Generate and insert sample data."""
    print(f"\n📊 Generating sample data with realistic row counts...")
    cursor = conn.cursor()

    # Sample data
    datacenters = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
    statuses = ['active', 'healthy', 'unhealthy', 'maintenance']
    lb_types = ['application', 'network', 'gateway']
    algorithms = ['round_robin', 'least_connections', 'ip_hash']

    for table_name, columns in tables.items():
        rows = []

        # Randomize row count for every table
        num_rows = random.randint(*ROW_COUNT_RANGE)

        for i in range(1, num_rows + 1):
            row = []

            for col in columns:
                col_name = col['name'].lower()
                col_type = get_sql_type(col['type']).upper()

                # Skip ID (auto-generated)
                if col_name == 'id':
                    continue

                # Generate data based on column name
                # Check for foreign keys first (they end with _id)
                if col_name.endswith('_id') and col_name != 'id':
                    value = random.randint(1, 50)
                elif 'name' in col_name:
                    value = f"{table_name[:-1]}-{i:03d}"
                elif 'status' in col_name:
                    value = random.choice(statuses)
                elif 'datacenter' in col_name or 'region' in col_name:
                    value = random.choice(datacenters)
                elif 'ip_address' in col_name or col_name == 'ip' or 'vip' in col_name:
                    value = f"10.0.{random.randint(1,255)}.{random.randint(1,254)}"
                elif 'port' in col_name:
                    value = random.choice([80, 443, 8080, 8443, 3306, 5432])
                elif 'type' in col_name:
                    value = random.choice(lb_types)
                elif 'algorithm' in col_name:
                    value = random.choice(algorithms)
                elif 'cpu' in col_name or 'memory' in col_name:
                    value = round(random.uniform(10, 90), 2)
                elif 'bandwidth' in col_name or 'traffic' in col_name or 'bytes' in col_name:
                    value = random.randint(1000, 1000000)
                elif 'requests' in col_name:
                    value = round(random.uniform(10, 1000), 2)
                elif 'created' in col_name or 'timestamp' in col_name or 'date' in col_name:
                    value = datetime.now() - timedelta(days=random.randint(0, 365))
                elif 'count' in col_name or 'connections' in col_name:
                    value = random.randint(1, 1000)
                elif 'enabled' in col_name or 'active' in col_name:
                    value = random.choice([True, False])
                else:
                    # Fallback: generate value based on column type
                    if col_type == 'INTEGER':
                        value = random.randint(1, 1000)
                    elif col_type == 'REAL':
                        value = round(random.uniform(1, 100), 2)
                    elif col_type == 'BOOLEAN':
                        value = random.choice([True, False])
                    elif col_type == 'TIMESTAMP':
                        value = datetime.now() - timedelta(days=random.randint(0, 365))
                    elif col_type == 'DATE':
                        value = (datetime.now() - timedelta(days=random.randint(0, 365))).date()
                    else:  # TEXT or unknown
                        value = f"{col_name}_{i}"

                row.append(value)

            rows.append(row)

        # Insert data
        col_names = [col['name'] for col in columns if col['name'].lower() != 'id']
        placeholders = ', '.join(['%s'] * len(col_names))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders})"

        execute_batch(cursor, insert_sql, rows)
        print(f"  ✅ {table_name}: {len(rows)} rows")

    conn.commit()
    cursor.close()


def main():
    print(f"\n{'='*60}")
    print(f"🚀 Production Data Generator")
    print(f"{'='*60}")
    print(f"📁 Excel: {EXCEL_FILE}")
    print(f"💾 Database: {DATABASE_URL}")

    # Check Excel exists
    if not os.path.exists(EXCEL_FILE):
        print(f"\n❌ Excel file not found: {EXCEL_FILE}")
        print("\nCreate Excel with 2 sheets:")
        print("  1. 'table_schema': table_name, column_name, column_type")
        print("  2. 'mapping': table_a, column_a, table_b, column_b")
        sys.exit(1)

    # Parse schema
    tables = parse_excel_schema()

    # Connect and create
    conn = connect_postgres()
    create_tables(conn, tables)
    generate_sample_data(conn, tables)
    conn.close()

    print(f"\n{'='*60}")
    print("✅ Sample production data created!")
    print(f"{'='*60}")
    print("\nNext:")
    print("  python scripts/schema_ingest.py build --output schemas/prod.json")
    print("  python gemini_cli.py 'Show me all load balancers'")


if __name__ == '__main__':
    main()
