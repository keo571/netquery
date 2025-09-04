"""
Network infrastructure sample data generator.
Creates realistic network operations data for monitoring and management.
"""
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import Table, Column, Integer, String, DateTime, Float, Text, ForeignKey
from src.text_to_sql.database.engine import get_metadata, get_engine, DatabaseSession

logger = logging.getLogger(__name__)

# Network infrastructure data patterns
LOAD_BALANCERS = [
    "lb-prod-web-01", "lb-prod-api-01", "lb-stage-web-01", "lb-dev-api-01",
    "lb-prod-db-01", "lb-prod-cache-01", "haproxy-web-01", "nginx-api-01"
]

SERVERS = [
    "web-01.prod.company.com", "web-02.prod.company.com", "api-01.prod.company.com",
    "db-01.prod.company.com", "cache-01.prod.company.com", "worker-01.prod.company.com",
    "web-01.stage.company.com", "api-01.stage.company.com"
]

VIP_ADDRESSES = [
    "10.0.1.100", "10.0.1.101", "10.0.1.102", "10.0.2.100",
    "192.168.1.100", "192.168.2.100", "172.16.1.100", "172.16.2.100"
]

DATA_CENTERS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
AVAILABILITY_ZONES = ["us-east-1a", "us-east-1b", "us-west-2a", "us-west-2c"]

LB_TYPES = ["application", "network", "gateway", "internal"]
LB_ALGORITHMS = ["round_robin", "least_connections", "ip_hash", "weighted"]
SERVER_ROLES = ["web", "api", "database", "cache", "worker", "proxy"]
SERVER_STATUSES = ["healthy", "unhealthy", "maintenance", "draining"]

SSL_PROVIDERS = ["DigiCert", "GlobalSign", "Let's Encrypt", "Cloudflare", "AWS"]
PROTOCOLS = ["HTTP", "HTTPS", "TCP", "UDP", "GRPC"]

MONITORING_METRICS = [
    "cpu_utilization", "memory_usage", "disk_io", "network_throughput",
    "response_time", "request_rate", "error_rate", "connection_count"
]


def create_infrastructure_schema(metadata):
    """Create network infrastructure database schema."""
    # Load balancers table
    load_balancers = Table('load_balancers', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False),
        Column('status', String(20), nullable=False),
        Column('vip_address', String(45)),
        Column('datacenter', String(50)),
        Column('lb_type', String(20)),
        Column('algorithm', String(30)),
        Column('created_at', DateTime, default=datetime.utcnow),
    )
    
    # Servers table
    servers = Table('servers', metadata,
        Column('id', Integer, primary_key=True),
        Column('hostname', String(255), nullable=False),
        Column('status', String(20), nullable=False),
        Column('cpu_utilization', Float),
        Column('memory_usage', Float),
        Column('datacenter', String(50)),
        Column('role', String(30)),
        Column('created_at', DateTime, default=datetime.utcnow),
    )
    
    # SSL certificates table
    ssl_certificates = Table('ssl_certificates', metadata,
        Column('id', Integer, primary_key=True),
        Column('domain', String(255), nullable=False),
        Column('issuer', String(100)),
        Column('expiry_date', DateTime),
        Column('status', String(20)),
        Column('provider', String(50)),
        Column('created_at', DateTime, default=datetime.utcnow),
    )
    
    # VIP pools table (junction table)
    vip_pools = Table('vip_pools', metadata,
        Column('id', Integer, primary_key=True),
        Column('vip_address', String(45), nullable=False),
        Column('port', Integer),
        Column('protocol', String(10)),
        Column('load_balancer_id', Integer, ForeignKey('load_balancers.id')),
        Column('created_at', DateTime, default=datetime.utcnow),
    )
    
    # Backend servers mapping
    backend_mappings = Table('backend_mappings', metadata,
        Column('id', Integer, primary_key=True),
        Column('load_balancer_id', Integer, ForeignKey('load_balancers.id')),
        Column('server_id', Integer, ForeignKey('servers.id')),
        Column('weight', Integer, default=1),
        Column('active', Integer, default=1),
        Column('created_at', DateTime, default=datetime.utcnow),
    )
    
    return {
        'load_balancers': load_balancers,
        'servers': servers,
        'ssl_certificates': ssl_certificates,
        'vip_pools': vip_pools,
        'backend_mappings': backend_mappings
    }


def generate_network_value(column_name: str, column_type: str, index: int) -> Any:
    """
    Generate appropriate network infrastructure value based on column name and type.
    
    Args:
        column_name: Name of the database column
        column_type: SQL type of the column
        index: Row index for generating unique values
        
    Returns:
        Generated value appropriate for network infrastructure
    """
    col_name = column_name.lower()
    col_type = column_type.lower()
    
    # Load balancer related
    if any(pattern in col_name for pattern in ['lb', 'loadbalancer', 'load_balancer']):
        if 'name' in col_name:
            return random.choice(LOAD_BALANCERS)
        elif 'type' in col_name:
            return random.choice(LB_TYPES)
        elif 'algorithm' in col_name:
            return random.choice(LB_ALGORITHMS)
    
    # Server related  
    elif any(pattern in col_name for pattern in ['server', 'host', 'node']):
        if 'name' in col_name or 'hostname' in col_name:
            return random.choice(SERVERS)
        elif 'role' in col_name:
            return random.choice(SERVER_ROLES)
    
    # Status fields (for both servers and load balancers)
    elif any(pattern in col_name for pattern in ['status', 'state']):
        return random.choice(SERVER_STATUSES)
    
    # VIP and IP addresses
    elif any(pattern in col_name for pattern in ['vip', 'virtual_ip']):
        return random.choice(VIP_ADDRESSES)
    elif 'ip' in col_name or ('address' in col_name and 'port' not in col_name):
        if 'vip' in col_name or 'virtual' in col_name:
            return random.choice(VIP_ADDRESSES)
        else:
            return f"10.0.{random.randint(1, 10)}.{random.randint(1, 254)}"
    
    # Location related
    elif any(pattern in col_name for pattern in ['datacenter', 'data_center', 'region']):
        return random.choice(DATA_CENTERS)
    elif any(pattern in col_name for pattern in ['zone', 'availability_zone']):
        return random.choice(AVAILABILITY_ZONES)
    
    # Network protocols and ports
    elif 'protocol' in col_name:
        return random.choice(PROTOCOLS)
    elif 'port' in col_name:
        port_map = {
            'https': 443, 'ssl': 443, 'http': 80,
            'ssh': 22, 'mysql': 3306, 'redis': 6379
        }
        for key, port in port_map.items():
            if key in col_name:
                return port
        return random.choice([80, 443, 8080, 8443, 3000, 5000, 9000])
    
    # SSL/Certificate related
    elif any(pattern in col_name for pattern in ['ssl', 'cert', 'certificate']):
        if 'provider' in col_name or 'issuer' in col_name:
            return random.choice(SSL_PROVIDERS)
        elif 'expir' in col_name:
            # Generate certificates with different expiry patterns:
            # 20% already expired, 20% expiring soon, 60% future expiry
            now = datetime.now()  # Get current time at generation
            rand = random.random()
            if rand < 0.2:  # Already expired
                return now - timedelta(days=random.randint(1, 90))
            elif rand < 0.4:  # Expiring in next 30 days  
                return now + timedelta(days=random.randint(1, 30))
            else:  # Future expiry
                return now + timedelta(days=random.randint(31, 365))
    
    # Metrics and monitoring
    elif 'metric' in col_name:
        if 'name' in col_name or 'type' in col_name:
            return random.choice(MONITORING_METRICS)
        elif 'value' in col_name:
            return round(random.uniform(0.0, 100.0), 2)
    
    # Performance values
    elif any(pattern in col_name for pattern in ['weight', 'priority']):
        return random.randint(1, 100)
    elif any(pattern in col_name for pattern in ['timeout', 'interval']):
        return random.randint(5, 300)
    
    # Dates
    elif any(pattern in col_name for pattern in ['created', 'updated', 'modified', 'date', 'time']):
        now = datetime.now()  # Get current time at generation
        return now - timedelta(days=random.randint(0, 365))
    
    # Handle by SQL type
    elif any(t in col_type for t in ['int', 'integer', 'number']):
        if 'id' in col_name:
            return index + 1
        elif 'connections' in col_name or 'count' in col_name:
            return random.randint(1, 1000)
        elif any(pattern in col_name for pattern in ['utilization', 'usage', 'percent']):
            return random.randint(0, 100)
        elif 'latency' in col_name or 'response_time' in col_name:
            return random.randint(1, 500)
        elif 'bandwidth' in col_name or 'throughput' in col_name:
            return random.randint(100, 10000)
        else:
            return random.randint(1, 1000)
    
    elif any(t in col_type for t in ['decimal', 'float', 'real']):
        if any(pattern in col_name for pattern in ['cpu', 'memory', 'disk']):
            return round(random.uniform(0.0, 100.0), 2)
        else:
            return round(random.uniform(0.0, 100.0), 2)
    
    elif any(t in col_type for t in ['bool', 'boolean']):
        return random.choice([True, False])
    
    elif any(t in col_type for t in ['text', 'varchar', 'char']):
        if 'id' in col_name:
            return f"{col_name}_{index + 1}"
        else:
            return f"network_{col_name}_{index + 1}"
    
    # Default fallback
    return f"value_{index + 1}"


def populate_table(session, table, records: int = 50) -> int:
    """
    Populate a single table with network infrastructure data.
    
    Args:
        session: Database session
        table: SQLAlchemy table object
        records: Number of records to create
        
    Returns:
        Number of records created
    """
    records_created = 0
    
    for i in range(records):
        try:
            # Generate data for each column
            record_data = {}
            for column in table.columns:
                # Skip auto-increment primary keys
                if column.primary_key and column.autoincrement:
                    continue
                
                # Handle foreign keys simply - just use index + 1
                if column.foreign_keys:
                    record_data[column.name] = (i % 10) + 1  # Simple cycling through IDs
                else:
                    # Generate appropriate value
                    value = generate_network_value(column.name, str(column.type), i)
                    if value is not None:
                        record_data[column.name] = value
            
            # Insert the record
            session.execute(table.insert().values(**record_data))
            records_created += 1
            
        except Exception as e:
            logger.warning(f"Failed to create record {i} for {table.name}: {e}")
            continue
    
    session.commit()
    logger.info(f"Created {records_created} records in {table.name}")
    return records_created


def create_infrastructure_database(tables: Optional[List[str]] = None, 
                                  records_per_table: int = 50) -> Dict[str, int]:
    """
    Create network infrastructure database schema and sample data.
    
    Args:
        tables: Specific tables to populate (None = all tables)
        records_per_table: Number of records per table
        
    Returns:
        Dictionary with table names and record counts
    """
    logger.info("Creating network infrastructure database...")
    
    engine = get_engine()
    metadata = get_metadata()
    
    # Check if tables already exist
    if not metadata.tables:
        logger.info("Creating database schema...")
        # Create fresh metadata and define schema
        from sqlalchemy import MetaData
        fresh_metadata = MetaData()
        schema_tables = create_infrastructure_schema(fresh_metadata)
        
        # Create all tables
        fresh_metadata.create_all(engine)
        logger.info("Database schema created successfully")
        
        # Use the schema we just created
        tables_to_use = schema_tables
    else:
        logger.info("Using existing database schema...")
        tables_to_use = metadata.tables
    
    # Determine which tables to populate
    target_tables = tables or list(tables_to_use.keys())
    results = {}
    
    with DatabaseSession() as session:
        for table_name in target_tables:
            if table_name in tables_to_use:
                table = tables_to_use[table_name]
                count = populate_table(session, table, records_per_table)
                results[table_name] = count
    
    logger.info(f"Network infrastructure data generation completed for {len(results)} tables")
    return results


if __name__ == "__main__":
    print("Creating network infrastructure database...")
    print(f"Database will be created at: infrastructure.db")
    
    result = create_infrastructure_database()
    
    print(f"✅ Successfully created network infrastructure database!")
    print(f"📊 Tables and record counts: {result}")
    print(f"📁 Database location: ./infrastructure.db")
    
    # Verify the database file was created
    import os
    if os.path.exists("infrastructure.db"):
        size = os.path.getsize("infrastructure.db")
        print(f"💾 Database file size: {size:,} bytes")
    else:
        print("⚠️  Database file not found!")