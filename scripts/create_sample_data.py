"""
Network infrastructure sample data generator.
Creates realistic network operations data using pure SQLite.
"""
import random
import sqlite3
import os
from datetime import datetime, timedelta, date


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
LB_TYPES = ["application", "network", "gateway", "internal"]
LB_ALGORITHMS = ["round_robin", "least_connections", "ip_hash", "weighted"]
SERVER_ROLES = ["web", "api", "database", "cache", "worker", "proxy"]
SERVER_STATUSES = ["healthy", "unhealthy", "maintenance", "draining"]
SSL_PROVIDERS = ["DigiCert", "GlobalSign", "Let's Encrypt", "Cloudflare", "AWS"]
PROTOCOLS = ["HTTP", "HTTPS", "TCP", "UDP", "GRPC"]


def create_database_schema(cursor):
    """Create all database tables with proper schema."""
    
    # Load balancers
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS load_balancers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        vip_address TEXT,
        datacenter TEXT,
        lb_type TEXT,
        algorithm TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Servers
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY,
        hostname TEXT NOT NULL,
        status TEXT NOT NULL,
        cpu_utilization REAL,
        memory_usage REAL,
        datacenter TEXT,
        role TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # SSL certificates
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ssl_certificates (
        id INTEGER PRIMARY KEY,
        domain TEXT NOT NULL,
        issuer TEXT,
        expiry_date DATETIME,
        status TEXT,
        provider TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # VIP pools
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vip_pools (
        id INTEGER PRIMARY KEY,
        vip_address TEXT NOT NULL,
        port INTEGER,
        protocol TEXT,
        load_balancer_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (load_balancer_id) REFERENCES load_balancers(id)
    )
    ''')
    
    # Backend mappings
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS backend_mappings (
        id INTEGER PRIMARY KEY,
        load_balancer_id INTEGER,
        server_id INTEGER,
        weight INTEGER DEFAULT 100,
        health_check_path TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (load_balancer_id) REFERENCES load_balancers(id),
        FOREIGN KEY (server_id) REFERENCES servers(id)
    )
    ''')
    
    # Network traffic monitoring
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS network_traffic (
        id INTEGER PRIMARY KEY,
        load_balancer_id INTEGER,
        timestamp DATETIME,
        requests_per_second INTEGER,
        response_time_ms REAL,
        bandwidth_mbps REAL,
        active_connections INTEGER,
        error_rate_percent REAL,
        FOREIGN KEY (load_balancer_id) REFERENCES load_balancers(id)
    )
    ''')
    
    # SSL monitoring
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ssl_monitoring (
        id INTEGER PRIMARY KEY,
        date DATE,
        certificates_expiring_30days INTEGER,
        certificates_expiring_7days INTEGER,
        total_certificates INTEGER,
        expired_certificates INTEGER,
        renewed_certificates INTEGER
    )
    ''')
    
    # Load balancer health log
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lb_health_log (
        id INTEGER PRIMARY KEY,
        load_balancer_id INTEGER,
        timestamp DATETIME,
        healthy_backends INTEGER,
        total_backends INTEGER,
        avg_response_time_ms REAL,
        total_requests INTEGER,
        health_score_percent REAL,
        FOREIGN KEY (load_balancer_id) REFERENCES load_balancers(id)
    )
    ''')
    
    # Network connectivity
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS network_connectivity (
        id INTEGER PRIMARY KEY,
        server_id INTEGER,
        timestamp DATETIME,
        latency_ms REAL,
        packet_loss_percent REAL,
        uptime_percent REAL,
        bandwidth_utilization_percent REAL,
        connection_count INTEGER,
        FOREIGN KEY (server_id) REFERENCES servers(id)
    )
    ''')


def generate_load_balancers(cursor, count=50):
    """Generate load balancer data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        data.append((
            random.choice(LOAD_BALANCERS),
            random.choice(SERVER_STATUSES),
            random.choice(VIP_ADDRESSES),
            random.choice(DATA_CENTERS),
            random.choice(LB_TYPES),
            random.choice(LB_ALGORITHMS),
            created
        ))
    
    cursor.executemany('''
        INSERT INTO load_balancers (name, status, vip_address, datacenter, lb_type, algorithm, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_servers(cursor, count=50):
    """Generate server data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        data.append((
            random.choice(SERVERS),
            random.choice(SERVER_STATUSES),
            round(random.uniform(0.0, 100.0), 2),  # cpu_utilization
            round(random.uniform(0.0, 100.0), 2),  # memory_usage
            random.choice(DATA_CENTERS),
            random.choice(SERVER_ROLES),
            created
        ))
    
    cursor.executemany('''
        INSERT INTO servers (hostname, status, cpu_utilization, memory_usage, datacenter, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_ssl_certificates(cursor, count=50):
    """Generate SSL certificate data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        
        # Generate expiry dates with realistic patterns
        rand = random.random()
        if rand < 0.2:  # 20% expired
            expiry = datetime.now() - timedelta(days=random.randint(1, 90))
        elif rand < 0.4:  # 20% expiring soon
            expiry = datetime.now() + timedelta(days=random.randint(1, 30))
        else:  # 60% future expiry
            expiry = datetime.now() + timedelta(days=random.randint(31, 365))
        
        data.append((
            f"example{i+1}.com",
            random.choice(SSL_PROVIDERS),
            expiry,
            "active" if expiry > datetime.now() else "expired",
            random.choice(SSL_PROVIDERS),
            created
        ))
    
    cursor.executemany('''
        INSERT INTO ssl_certificates (domain, issuer, expiry_date, status, provider, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_vip_pools(cursor, count=50):
    """Generate VIP pool data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        data.append((
            random.choice(VIP_ADDRESSES),
            random.choice([80, 443, 8080, 8443, 3000, 5000, 9000]),
            random.choice(PROTOCOLS),
            (i % 50) + 1,  # load_balancer_id (cycling through available LBs)
            created
        ))
    
    cursor.executemany('''
        INSERT INTO vip_pools (vip_address, port, protocol, load_balancer_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_backend_mappings(cursor, count=50):
    """Generate backend mapping data."""
    data = []
    for i in range(count):
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        data.append((
            (i % 50) + 1,  # load_balancer_id
            (i % 50) + 1,  # server_id
            random.randint(1, 100),  # weight
            "/health",
            created
        ))
    
    cursor.executemany('''
        INSERT INTO backend_mappings (load_balancer_id, server_id, weight, health_check_path, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_network_traffic(cursor):
    """Generate network traffic monitoring data."""
    data = []
    base_time = datetime(2025, 1, 9, 0, 0, 0)
    
    # Generate 7 days of hourly data for first 5 load balancers
    for day in range(7):
        for hour in range(24):
            timestamp = base_time + timedelta(days=day, hours=hour)
            for lb_id in range(1, 6):
                data.append((
                    lb_id,
                    timestamp,
                    random.randint(100, 1000),  # requests_per_second
                    round(random.uniform(50, 200), 2),  # response_time_ms
                    round(random.uniform(10, 100), 2),  # bandwidth_mbps
                    random.randint(50, 200),  # active_connections
                    round(random.uniform(0.1, 2.0), 2)  # error_rate_percent
                ))
    
    cursor.executemany('''
        INSERT INTO network_traffic (load_balancer_id, timestamp, requests_per_second, response_time_ms, bandwidth_mbps, active_connections, error_rate_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_ssl_monitoring(cursor):
    """Generate SSL monitoring data."""
    data = []
    base_date = date(2025, 1, 1)
    
    # Generate 30 days of daily SSL monitoring data
    for day in range(30):
        monitoring_date = base_date + timedelta(days=day)
        data.append((
            monitoring_date,
            random.randint(0, 5),  # certificates_expiring_30days
            random.randint(0, 2),  # certificates_expiring_7days
            50,  # total_certificates
            random.randint(0, 2),  # expired_certificates
            random.randint(0, 3)   # renewed_certificates
        ))
    
    cursor.executemany('''
        INSERT INTO ssl_monitoring (date, certificates_expiring_30days, certificates_expiring_7days, total_certificates, expired_certificates, renewed_certificates)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_lb_health_log(cursor):
    """Generate load balancer health log data."""
    data = []
    base_time = datetime(2025, 1, 9, 0, 0, 0)
    
    # Generate 3 days of hourly health data for first 10 load balancers
    for day in range(3):
        for hour in range(24):
            timestamp = base_time + timedelta(days=day, hours=hour)
            for lb_id in range(1, 11):
                total_backends = random.randint(2, 8)
                healthy_backends = random.randint(0, total_backends)
                health_score = (healthy_backends / total_backends) * 100
                
                data.append((
                    lb_id,
                    timestamp,
                    healthy_backends,
                    total_backends,
                    round(random.uniform(50, 200), 2),  # avg_response_time_ms
                    random.randint(1000, 10000),  # total_requests
                    round(health_score, 2)  # health_score_percent
                ))
    
    cursor.executemany('''
        INSERT INTO lb_health_log (load_balancer_id, timestamp, healthy_backends, total_backends, avg_response_time_ms, total_requests, health_score_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def generate_network_connectivity(cursor):
    """Generate network connectivity data."""
    data = []
    base_time = datetime(2025, 1, 9, 0, 0, 0)
    
    # Generate 2 days of hourly connectivity data for first 20 servers
    for day in range(2):
        for hour in range(24):
            timestamp = base_time + timedelta(days=day, hours=hour)
            for server_id in range(1, 21):
                # Simulate network conditions
                latency = round(random.uniform(1.2, 15.8), 2)
                packet_loss = round(random.uniform(0.0, 2.5), 2)
                
                # Occasional network issues
                if random.random() < 0.05:  # 5% chance of issues
                    latency *= random.uniform(2, 5)
                    packet_loss *= random.uniform(2, 10)
                    uptime = round(random.uniform(85, 95), 2)
                else:
                    uptime = round(random.uniform(98, 100), 2)
                
                data.append((
                    server_id,
                    timestamp,
                    round(latency, 2),
                    round(packet_loss, 2),
                    uptime,
                    round(random.uniform(20, 85), 2),  # bandwidth_utilization_percent
                    random.randint(50, 300)  # connection_count
                ))
    
    cursor.executemany('''
        INSERT INTO network_connectivity (server_id, timestamp, latency_ms, packet_loss_percent, uptime_percent, bandwidth_utilization_percent, connection_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)
    return len(data)


def create_infrastructure_database():
    """Create complete network infrastructure database."""
    print("Creating network infrastructure database...")
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect('data/infrastructure.db')
    cursor = conn.cursor()
    
    try:
        # Create schema
        print("Creating database schema...")
        create_database_schema(cursor)
        
        # Generate infrastructure data
        print("Generating infrastructure data...")
        results = {}
        results['load_balancers'] = generate_load_balancers(cursor)
        results['servers'] = generate_servers(cursor)
        results['ssl_certificates'] = generate_ssl_certificates(cursor)
        results['vip_pools'] = generate_vip_pools(cursor)
        results['backend_mappings'] = generate_backend_mappings(cursor)
        
        # Generate monitoring data
        print("Generating monitoring data...")
        results['network_traffic'] = generate_network_traffic(cursor)
        results['ssl_monitoring'] = generate_ssl_monitoring(cursor)
        results['lb_health_log'] = generate_lb_health_log(cursor)
        results['network_connectivity'] = generate_network_connectivity(cursor)
        
        # Commit all changes
        conn.commit()
        
        return results
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("Creating network infrastructure database...")
    print(f"Database will be created at: data/infrastructure.db")
    
    result = create_infrastructure_database()
    
    print(f"✅ Successfully created network infrastructure database!")
    print(f"📊 Tables and record counts: {result}")
    print(f"📁 Database location: ./data/infrastructure.db")
    
    # Verify the database file was created
    if os.path.exists("data/infrastructure.db"):
        size = os.path.getsize("data/infrastructure.db")
        print(f"💾 Database file size: {size:,} bytes")
    else:
        print("⚠️  Database file not found!")