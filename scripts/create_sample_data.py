"""
Network infrastructure sample data generator.
Creates realistic network operations data matching sample_schema.json.
NO FOREIGN KEYS, NO PRIMARY KEYS - mimics real-world databases without proper constraints.
"""
import random
import os
import argparse
from datetime import datetime, timedelta, date
from urllib.parse import urlparse

# Try importing psycopg2 for PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import execute_batch
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# SQLite support
import sqlite3

# Configure SQLite to handle datetime properly (fixes Python 3.12 warnings)
def adapt_datetime(dt):
    """Convert datetime to ISO string for SQLite storage."""
    return dt.isoformat()

def adapt_date(d):
    """Convert date to ISO string for SQLite storage."""
    return d.isoformat()

# Register adapters to avoid deprecation warnings
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_adapter(date, adapt_date)


# Network infrastructure data patterns
LOAD_BALANCERS = [
    "lb-prod-web-01", "lb-prod-api-01", "lb-stage-web-01", "lb-dev-api-01",
    "lb-prod-db-01", "lb-prod-cache-01", "haproxy-web-01", "nginx-api-01",
    "lb-prod-app-01", "lb-stage-api-01"
]

BACKEND_SERVERS = [
    "web-01.prod.company.com", "web-02.prod.company.com", "api-01.prod.company.com",
    "db-01.prod.company.com", "cache-01.prod.company.com", "worker-01.prod.company.com",
    "web-01.stage.company.com", "api-01.stage.company.com", "app-01.prod.company.com",
    "app-02.prod.company.com"
]

VIP_ADDRESSES = [
    "10.0.1.100", "10.0.1.101", "10.0.1.102", "10.0.2.100",
    "192.168.1.100", "192.168.2.100", "172.16.1.100", "172.16.2.100"
]

DOMAIN_NAMES = [
    "app.example.com", "api.example.com", "www.example.com",
    "cdn.example.com", "admin.example.com", "mobile.example.com"
]

DATA_CENTERS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
STATUSES = ["active", "inactive", "maintenance"]
HEALTH_STATUSES = ["up", "down", "unknown"]
LB_METHODS = ["round-robin", "geo", "ratio", "weighted"]
PROTOCOLS = ["HTTP", "HTTPS", "TCP", "UDP"]
POOL_NAMES = ["web-pool", "api-pool", "app-pool", "db-pool", "cache-pool"]


def create_database_schema(cursor, db_type='sqlite'):
    """Create all database tables matching sample_schema.json.

    NO FOREIGN KEYS, NO PRIMARY KEYS - mimics real-world databases without proper constraints.

    Args:
        cursor: Database cursor
        db_type: 'sqlite' or 'postgres'
    """
    # Adjust data types based on database
    if db_type == 'postgres':
        int_type = 'SERIAL'
        text_type = 'VARCHAR'
        datetime_type = 'TIMESTAMP'
        decimal_type = 'DECIMAL'
        bigint_type = 'BIGINT'
        boolean_type = 'BOOLEAN'
        default_timestamp = 'DEFAULT NOW()'
    else:
        int_type = 'INTEGER'
        text_type = 'TEXT'
        datetime_type = 'DATETIME'
        decimal_type = 'REAL'
        bigint_type = 'INTEGER'
        boolean_type = 'INTEGER'
        default_timestamp = 'DEFAULT CURRENT_TIMESTAMP'

    # Table 1: load_balancers
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS load_balancers (
        id {int_type},
        name {text_type} NOT NULL,
        ip_address {text_type},
        status {text_type} NOT NULL,
        datacenter {text_type} NOT NULL,
        created_at {datetime_type} {default_timestamp}
    )
    ''')

    # Table 2: virtual_ips
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS virtual_ips (
        id {int_type},
        vip_address {text_type} NOT NULL,
        port INTEGER NOT NULL,
        protocol {text_type} NOT NULL,
        load_balancer_id INTEGER NOT NULL,
        pool_name {text_type} NOT NULL,
        health_check_url {text_type},
        created_at {datetime_type} {default_timestamp}
    )
    ''')

    # Table 3: wide_ips
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS wide_ips (
        id {int_type},
        domain_name {text_type} NOT NULL,
        load_balancing_method {text_type} NOT NULL,
        ttl INTEGER,
        status {text_type} NOT NULL,
        created_at {datetime_type} {default_timestamp}
    )
    ''')

    # Table 4: wide_ip_pools
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS wide_ip_pools (
        id {int_type},
        wide_ip_id INTEGER NOT NULL,
        virtual_ip_id INTEGER NOT NULL,
        priority INTEGER,
        ratio INTEGER,
        enabled {boolean_type} NOT NULL
    )
    ''')

    # Table 5: backend_servers
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS backend_servers (
        id {int_type},
        hostname {text_type} NOT NULL,
        ip_address {text_type} NOT NULL,
        port INTEGER NOT NULL,
        pool_name {text_type} NOT NULL,
        load_balancer_id INTEGER NOT NULL,
        health_status {text_type},
        datacenter {text_type} NOT NULL
    )
    ''')

    # Table 6: traffic_stats
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS traffic_stats (
        id {int_type},
        virtual_ip_id INTEGER NOT NULL,
        timestamp {datetime_type} NOT NULL,
        requests_per_second {decimal_type},
        bytes_in {bigint_type},
        bytes_out {bigint_type},
        active_connections INTEGER
    )
    ''')


def generate_load_balancers(cursor, count=50):
    """Generate load balancer data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        data.append((
            i + 1,  # Manual id assignment (no auto-increment)
            random.choice(LOAD_BALANCERS),
            f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            random.choice(STATUSES),
            random.choice(DATA_CENTERS),
            created
        ))

    cursor.executemany('''
        INSERT INTO load_balancers (id, name, ip_address, status, datacenter, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_virtual_ips(cursor, count=50):
    """Generate virtual IP data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        data.append((
            i + 1,  # Manual id assignment (no auto-increment)
            random.choice(VIP_ADDRESSES),
            random.choice([80, 443, 8080, 8443, 3000, 5000, 9000]),
            random.choice(PROTOCOLS),
            random.randint(1, 50),  # load_balancer_id (no FK constraint)
            random.choice(POOL_NAMES),
            f"/health" if random.random() > 0.3 else None,
            created
        ))

    cursor.executemany('''
        INSERT INTO virtual_ips (id, vip_address, port, protocol, load_balancer_id, pool_name, health_check_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_wide_ips(cursor, count=20):
    """Generate wide IP (GSLB) data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        data.append((
            i + 1,  # Manual id assignment (no auto-increment)
            random.choice(DOMAIN_NAMES),
            random.choice(LB_METHODS),
            random.choice([60, 120, 300, 600, 1800]),  # TTL in seconds
            random.choice(["enabled", "disabled"]),
            created
        ))

    cursor.executemany('''
        INSERT INTO wide_ips (id, domain_name, load_balancing_method, ttl, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_wide_ip_pools(cursor, count=40):
    """Generate wide IP pool mappings."""
    data = []
    for i in range(count):
        data.append((
            i + 1,  # Manual id assignment (no auto-increment)
            random.randint(1, 20),  # wide_ip_id (no FK constraint)
            random.randint(1, 50),  # virtual_ip_id (no FK constraint)
            random.randint(1, 100) if random.random() > 0.3 else None,  # priority
            random.randint(1, 10) if random.random() > 0.3 else None,   # ratio
            1 if random.random() > 0.1 else 0  # enabled (90% enabled)
        ))

    cursor.executemany('''
        INSERT INTO wide_ip_pools (id, wide_ip_id, virtual_ip_id, priority, ratio, enabled)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_backend_servers(cursor, count=50):
    """Generate backend server data."""
    data = []
    for i in range(count):
        data.append((
            i + 1,  # Manual id assignment (no auto-increment)
            random.choice(BACKEND_SERVERS),
            f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            random.choice([80, 443, 8080, 8443, 3000, 5000, 9000]),
            random.choice(POOL_NAMES),
            random.randint(1, 50),  # load_balancer_id (no FK constraint)
            random.choice(HEALTH_STATUSES) if random.random() > 0.2 else None,
            random.choice(DATA_CENTERS)
        ))

    cursor.executemany('''
        INSERT INTO backend_servers (id, hostname, ip_address, port, pool_name, load_balancer_id, health_status, datacenter)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_traffic_stats(cursor):
    """Generate traffic statistics data."""
    data = []
    base_time = datetime(2025, 11, 23, 0, 0, 0)

    # Generate 7 days of hourly data for first 10 virtual IPs (Nov 23 - Nov 30, 2025)
    record_id = 1
    for day in range(7):
        for hour in range(24):
            timestamp = base_time + timedelta(days=day, hours=hour)
            for vip_id in range(1, 11):
                data.append((
                    record_id,  # Manual id assignment (no auto-increment)
                    vip_id,  # virtual_ip_id (no FK constraint)
                    timestamp,
                    round(random.uniform(10.0, 1000.0), 2),  # requests_per_second
                    random.randint(1000000, 100000000),       # bytes_in
                    random.randint(5000000, 500000000),       # bytes_out
                    random.randint(50, 500)                   # active_connections
                ))
                record_id += 1

    cursor.executemany('''
        INSERT INTO traffic_stats (id, virtual_ip_id, timestamp, requests_per_second, bytes_in, bytes_out, active_connections)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def create_infrastructure_database(database_url=None):
    """Create complete network infrastructure database matching sample_schema.json.

    Args:
        database_url: Database connection URL. Supports:
                     - PostgreSQL: postgresql://user:pass@host:port/dbname
                     - SQLite: sqlite:///path/to/db.db or None (defaults to data/sample.db)

    Returns:
        dict: Table names and record counts
    """
    print("Creating network infrastructure database (matching sample_schema.json)...")

    # Determine database type
    if database_url and database_url.startswith('postgresql'):
        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 is not installed. Install with: pip install psycopg2-binary")
        db_type = 'postgres'
        print(f"Using PostgreSQL: {database_url}")
    else:
        db_type = 'sqlite'
        if not database_url or database_url.startswith('sqlite'):
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            # Extract path from sqlite:/// URL or use default
            if database_url and database_url.startswith('sqlite:///'):
                database_url = database_url.replace('sqlite:///', '')
            else:
                database_url = 'data/sample.db'
        print(f"Using SQLite: {database_url}")

    # Connect to database
    if db_type == 'postgres':
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
    else:
        conn = sqlite3.connect(database_url)

    cursor = conn.cursor()

    try:
        # Create schema
        print("Creating database schema (NO FOREIGN KEYS, NO PRIMARY KEYS - mimics real-world databases)...")
        create_database_schema(cursor, db_type=db_type)

        # Clear existing data to prevent duplicates
        print("Clearing existing data...")
        tables_to_clear = [
            'traffic_stats', 'backend_servers', 'wide_ip_pools',
            'wide_ips', 'virtual_ips', 'load_balancers'
        ]
        for table in tables_to_clear:
            cursor.execute(f'DELETE FROM {table}')

        # Generate infrastructure data
        print("Generating infrastructure data...")
        results = {}
        results['load_balancers'] = generate_load_balancers(cursor)
        results['virtual_ips'] = generate_virtual_ips(cursor)
        results['wide_ips'] = generate_wide_ips(cursor)
        results['wide_ip_pools'] = generate_wide_ip_pools(cursor)
        results['backend_servers'] = generate_backend_servers(cursor)

        # Generate monitoring data
        print("Generating traffic statistics...")
        results['traffic_stats'] = generate_traffic_stats(cursor)

        # Commit all changes
        conn.commit()

        return results

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create sample network infrastructure data (matching sample_schema.json)')
    parser.add_argument(
        '--database-url',
        type=str,
        help='Database URL (postgresql://... or sqlite:///...). Defaults to SQLite at data/sample.db'
    )
    args = parser.parse_args()

    # Use DATABASE_URL environment variable if not provided
    database_url = args.database_url or os.getenv('DATABASE_URL')

    result = create_infrastructure_database(database_url)

    print(f"✅ Successfully created network infrastructure database!")
    print(f"📊 Tables and record counts: {result}")

    # Verify SQLite database file if applicable
    if not database_url or database_url.startswith('sqlite') or not database_url.startswith('postgresql'):
        db_path = database_url if database_url and not database_url.startswith('sqlite') else 'data/sample.db'
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"💾 Database file size: {size:,} bytes")
            print(f"📁 Database location: {db_path}")
        else:
            print(f"⚠️  Database file not found: {db_path}")
