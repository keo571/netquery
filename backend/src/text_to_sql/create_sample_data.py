#!/usr/bin/env python3
"""
Infrastructure-focused sample database for Text-to-SQL agent.
Based on sql-agent implementation but with enhanced infrastructure tables.
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class InfrastructureDatabaseCreator:
    """Creates infrastructure-focused sample database."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Create data directory if it doesn't exist
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "infrastructure.db")
        
        self.db_path = db_path
        
        # Remove existing database to start fresh
        if os.path.exists(db_path):
            os.remove(db_path)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
    def create_all_tables(self):
        """Create all infrastructure tables and data."""
        logger.info("Creating infrastructure database tables...")
        
        self.create_infrastructure_schema()
        self.insert_sample_data()
        self.create_views()
        
        self.conn.commit()
        logger.info(f"Infrastructure database created successfully at: {self.db_path}")
    
    def create_infrastructure_schema(self):
        """Create infrastructure-specific tables."""
        
        # Data Centers
        self.conn.execute("""
            CREATE TABLE datacenters (
                dc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dc_name VARCHAR(50) NOT NULL UNIQUE,
                region VARCHAR(50),
                country VARCHAR(50),
                city VARCHAR(50),
                capacity INTEGER,
                power_usage_kw DECIMAL(8,2),
                status VARCHAR(20) DEFAULT 'active',
                established_date DATE
            )
        """)
        
        # Network Zones  
        self.conn.execute("""
            CREATE TABLE network_zones (
                zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_name VARCHAR(100),
                dc_id INTEGER,
                subnet VARCHAR(20),
                vlan_id INTEGER,
                security_level VARCHAR(20) DEFAULT 'internal',
                FOREIGN KEY (dc_id) REFERENCES datacenters(dc_id)
            )
        """)
        
        # VIP (Enhanced from your sql-agent version)
        self.conn.execute("""
            CREATE TABLE vip (
                vip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vip_address VARCHAR(45) NOT NULL,
                port INTEGER NOT NULL,
                protocol VARCHAR(10) DEFAULT 'HTTP',
                zone_id INTEGER,
                service_name VARCHAR(100),
                health_check_url VARCHAR(200),
                status VARCHAR(20) DEFAULT 'active',
                created_date DATETIME DEFAULT (datetime('now')),
                FOREIGN KEY (zone_id) REFERENCES network_zones(zone_id)
            )
        """)
        
        # Load Balancer (Enhanced from your sql-agent version)
        self.conn.execute("""
            CREATE TABLE load_balancer (
                device_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name VARCHAR(100) NOT NULL,
                location VARCHAR(100) NOT NULL,
                dc_id INTEGER,
                zone_id INTEGER,
                model VARCHAR(50),
                serial_number VARCHAR(100),
                management_ip VARCHAR(45),
                cpu_cores INTEGER,
                memory_gb INTEGER,
                throughput_mbps INTEGER,
                status VARCHAR(20) DEFAULT 'active',
                last_health_check DATETIME,
                firmware_version VARCHAR(50),
                FOREIGN KEY (dc_id) REFERENCES datacenters(dc_id),
                FOREIGN KEY (zone_id) REFERENCES network_zones(zone_id)
            )
        """)
        
        # VIP Load Balancer Assignment (Many-to-Many relationship)
        self.conn.execute("""
            CREATE TABLE vip_load_balancer (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vip_id INTEGER,
                device_id INTEGER,
                is_primary BOOLEAN DEFAULT 0,
                weight INTEGER DEFAULT 100,
                assigned_date DATETIME DEFAULT (datetime('now')),
                FOREIGN KEY (vip_id) REFERENCES vip(vip_id),
                FOREIGN KEY (device_id) REFERENCES load_balancer(device_id),
                UNIQUE(vip_id, device_id)
            )
        """)
        
        # VIP Member (Enhanced from your sql-agent version)
        self.conn.execute("""
            CREATE TABLE vip_member (
                member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vip_id INTEGER NOT NULL,
                member_address VARCHAR(45) NOT NULL,
                port INTEGER NOT NULL,
                zone_id INTEGER,
                server_type VARCHAR(50),
                os_version VARCHAR(100),
                cpu_cores INTEGER,
                memory_gb INTEGER,
                disk_gb INTEGER,
                status VARCHAR(20) DEFAULT 'active',
                health_status VARCHAR(20) DEFAULT 'unknown',
                response_time_ms INTEGER,
                last_check DATETIME,
                weight INTEGER DEFAULT 100,
                FOREIGN KEY (vip_id) REFERENCES vip(vip_id),
                FOREIGN KEY (zone_id) REFERENCES network_zones(zone_id)
            )
        """)
        
        # Network Interfaces
        self.conn.execute("""
            CREATE TABLE network_interfaces (
                interface_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                interface_name VARCHAR(50),
                ip_address VARCHAR(45),
                subnet_mask VARCHAR(45),
                interface_type VARCHAR(20),
                status VARCHAR(20) DEFAULT 'up',
                speed_mbps INTEGER,
                duplex VARCHAR(10),
                mtu INTEGER DEFAULT 1500,
                FOREIGN KEY (device_id) REFERENCES load_balancer(device_id)
            )
        """)
        
        # SSL Certificates
        self.conn.execute("""
            CREATE TABLE ssl_certificates (
                cert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                common_name VARCHAR(255),
                issuer VARCHAR(255),
                serial_number VARCHAR(100),
                valid_from DATE,
                valid_to DATE,
                key_size INTEGER,
                signature_algorithm VARCHAR(50),
                status VARCHAR(20) DEFAULT 'active'
            )
        """)
        
        # VIP SSL Bindings
        self.conn.execute("""
            CREATE TABLE vip_ssl_bindings (
                binding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vip_id INTEGER,
                cert_id INTEGER,
                binding_order INTEGER DEFAULT 1,
                FOREIGN KEY (vip_id) REFERENCES vip(vip_id),
                FOREIGN KEY (cert_id) REFERENCES ssl_certificates(cert_id)
            )
        """)

                # Wide IP (WIP) for Global Traffic Management
        self.conn.execute("""
            CREATE TABLE wip (
                wip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wip_name VARCHAR(255) NOT NULL,
                domain_name VARCHAR(255) NOT NULL UNIQUE,
                wip_type VARCHAR(20) DEFAULT 'A',
                ttl INTEGER DEFAULT 300,
                persistence VARCHAR(50) DEFAULT 'none',
                load_balancing_method VARCHAR(50) DEFAULT 'round_robin',
                status VARCHAR(20) DEFAULT 'active',
                health_check_interval INTEGER DEFAULT 30,
                created_date DATETIME DEFAULT (datetime('now')),
                description TEXT
            )
        """)
        
        # WIP Pools - Groups of virtual servers for WIP
        self.conn.execute("""
            CREATE TABLE wip_pools (
                pool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_name VARCHAR(100) NOT NULL,
                wip_id INTEGER,
                load_balancing_method VARCHAR(50) DEFAULT 'round_robin',
                priority INTEGER DEFAULT 100,
                ratio INTEGER DEFAULT 1,
                status VARCHAR(20) DEFAULT 'active',
                health_check_enabled BOOLEAN DEFAULT 1,
                fallback_mode VARCHAR(50) DEFAULT 'return_to_dns',
                created_date DATETIME DEFAULT (datetime('now')),
                FOREIGN KEY (wip_id) REFERENCES wip(wip_id)
            )
        """)
        
        # WIP Pool Members - VIPs that are members of WIP pools
        self.conn.execute("""
            CREATE TABLE wip_pool_members (
                member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_id INTEGER,
                vip_id INTEGER,
                dc_id INTEGER,
                member_order INTEGER DEFAULT 1,
                ratio INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 100,
                status VARCHAR(20) DEFAULT 'active',
                health_status VARCHAR(20) DEFAULT 'unknown',
                response_time_ms INTEGER,
                last_health_check DATETIME,
                enabled BOOLEAN DEFAULT 1,
                FOREIGN KEY (pool_id) REFERENCES wip_pools(pool_id),
                FOREIGN KEY (vip_id) REFERENCES vip(vip_id),
                FOREIGN KEY (dc_id) REFERENCES datacenters(dc_id)
            )
        """)
        
        # DNS Zones for WIP management
        self.conn.execute("""
            CREATE TABLE dns_zones (
                zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_name VARCHAR(255) NOT NULL UNIQUE,
                zone_type VARCHAR(20) DEFAULT 'forward',
                primary_dns VARCHAR(45),
                secondary_dns VARCHAR(45),
                refresh_interval INTEGER DEFAULT 3600,
                retry_interval INTEGER DEFAULT 600,
                expire_time INTEGER DEFAULT 604800,
                minimum_ttl INTEGER DEFAULT 300,
                status VARCHAR(20) DEFAULT 'active'
            )
        """)
        
        # Geographic regions for location-based routing
        self.conn.execute("""
            CREATE TABLE geo_regions (
                region_id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_name VARCHAR(100) NOT NULL,
                region_code VARCHAR(10),
                continent VARCHAR(50),
                country_codes TEXT,
                description TEXT
            )
        """)
        
        # WIP geographic routing rules
        self.conn.execute("""
            CREATE TABLE wip_geo_routing (
                routing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wip_id INTEGER,
                region_id INTEGER,
                pool_id INTEGER,
                priority INTEGER DEFAULT 100,
                enabled BOOLEAN DEFAULT 1,
                FOREIGN KEY (wip_id) REFERENCES wip(wip_id),
                FOREIGN KEY (region_id) REFERENCES geo_regions(region_id),
                FOREIGN KEY (pool_id) REFERENCES wip_pools(pool_id)
            )
        """)
    
    def insert_sample_data(self):
        """Insert infrastructure sample data."""
        logger.info("Inserting infrastructure sample data...")
        
        # Data Centers
        self.conn.executemany("""
            INSERT INTO datacenters (dc_name, region, country, city, capacity, power_usage_kw, established_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ('US-East-1', 'North America', 'USA', 'Virginia', 1000, 2500.5, '2018-01-15'),
            ('US-West-1', 'North America', 'USA', 'California', 800, 2100.0, '2019-06-20'),
            ('EU-Central-1', 'Europe', 'Germany', 'Frankfurt', 600, 1800.3, '2020-03-10'),
            ('AP-Southeast-1', 'Asia Pacific', 'Singapore', 'Singapore', 400, 1200.8, '2021-09-05')
        ])
        
        # Network Zones
        self.conn.executemany("""
            INSERT INTO network_zones (zone_name, dc_id, subnet, vlan_id, security_level) 
            VALUES (?, ?, ?, ?, ?)
        """, [
            ('DMZ', 1, '10.1.0.0/24', 100, 'public'),
            ('Internal', 1, '10.1.1.0/24', 101, 'internal'),
            ('Management', 1, '10.1.2.0/24', 102, 'restricted'),
            ('DMZ', 2, '10.2.0.0/24', 200, 'public'),
            ('Internal', 2, '10.2.1.0/24', 201, 'internal'),
            ('DMZ', 3, '10.3.0.0/24', 300, 'public'),
            ('Internal', 3, '10.3.1.0/24', 301, 'internal'),
            ('DMZ', 4, '10.4.0.0/24', 400, 'public')
        ])
        
        # Load Balancers
        lb_data = [
            ('lb-prod-1', 'US-East', 1, 1, 'F5-BIG-IP-4000', 'F5-001-2023', '10.1.2.10', 8, 32, 10000, 'active', '2024-01-15 10:30:00', '15.1.2'),
            ('lb-prod-2', 'US-East', 1, 1, 'F5-BIG-IP-4000', 'F5-002-2023', '10.1.2.11', 8, 32, 10000, 'active', '2024-01-15 10:32:00', '15.1.2'),
            ('lb-west-1', 'US-West', 2, 4, 'HAProxy-Enterprise', 'HAP-001-2023', '10.2.2.10', 4, 16, 5000, 'active', '2024-01-15 10:25:00', '2.8.1'),
            ('lb-eu-1', 'EU-Central', 3, 6, 'NGINX-Plus', 'NGX-001-2023', '10.3.2.10', 6, 24, 8000, 'active', '2024-01-15 10:28:00', '1.24.0'),
            ('lb-ap-1', 'AP-Southeast', 4, 8, 'Citrix-ADC', 'CTX-001-2023', '10.4.2.10', 4, 16, 6000, 'maintenance', '2024-01-14 15:20:00', '13.1.30')
        ]
        
        self.conn.executemany("""
            INSERT INTO load_balancer 
            (device_name, location, dc_id, zone_id, model, serial_number, management_ip, 
             cpu_cores, memory_gb, throughput_mbps, status, last_health_check, firmware_version) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, lb_data)
        
        # VIPs (Enhanced from your original)
        vip_data = [
            ('10.1.0.100', 80, 'HTTP', 1, 'web-frontend', '/health', 'active', '2024-01-15 08:00:00'),
            ('10.1.0.101', 443, 'HTTPS', 1, 'api-backend', '/api/health', 'active', '2024-01-15 08:00:00'),
            ('10.1.0.102', 8443, 'HTTPS', 2, 'admin-portal', '/admin/status', 'active', '2024-01-15 08:00:00'),
            ('10.2.0.100', 3306, 'TCP', 4, 'database-cluster', None, 'active', '2024-01-15 08:00:00'),
            ('10.3.0.100', 6379, 'TCP', 6, 'cache-layer', '/ping', 'active', '2024-01-15 08:00:00'),
            ('10.4.0.100', 443, 'HTTPS', 8, 'file-storage', '/storage/health', 'maintenance', '2024-01-14 20:00:00')
        ]
        
        self.conn.executemany("""
            INSERT INTO vip (vip_address, port, protocol, zone_id, service_name, health_check_url, status, created_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, vip_data)
        
        # VIP Load Balancer Assignments
        self.conn.executemany("""
            INSERT INTO vip_load_balancer (vip_id, device_id, is_primary, weight) 
            VALUES (?, ?, ?, ?)
        """, [
            (1, 1, 1, 100),  # web-frontend on lb-prod-1 (primary)
            (1, 2, 0, 50),   # web-frontend on lb-prod-2 (backup)
            (2, 1, 1, 100),  # api-backend on lb-prod-1 (primary)
            (2, 2, 0, 50),   # api-backend on lb-prod-2 (backup)
            (3, 2, 1, 100),  # admin-portal on lb-prod-2 (primary)
            (4, 3, 1, 100),  # database-cluster on lb-west-1
            (5, 4, 1, 100),  # cache-layer on lb-eu-1
            (6, 5, 1, 100)   # file-storage on lb-ap-1
        ])
        
        # VIP Members (Enhanced from your original)
        members_data = [
            (1, '192.168.1.10', 8080, 2, 'web', 'Ubuntu 22.04', 4, 16, 100, 'active', 'healthy', 45, '2024-01-15 11:00:00', 100),
            (1, '192.168.1.11', 8080, 2, 'web', 'Ubuntu 22.04', 4, 16, 100, 'active', 'healthy', 52, '2024-01-15 11:00:00', 100),
            (1, '192.168.1.12', 8080, 2, 'web', 'Ubuntu 22.04', 4, 16, 100, 'active', 'degraded', 89, '2024-01-15 10:55:00', 50),
            (2, '192.168.2.10', 3000, 2, 'api', 'Ubuntu 22.04', 8, 32, 200, 'active', 'healthy', 78, '2024-01-15 11:00:00', 100),
            (2, '192.168.2.11', 3000, 2, 'api', 'Ubuntu 22.04', 8, 32, 200, 'active', 'healthy', 85, '2024-01-15 11:00:00', 100),
            (4, '192.168.3.10', 3306, 5, 'database', 'Ubuntu 20.04', 16, 64, 500, 'active', 'healthy', 23, '2024-01-15 11:00:00', 100),
            (4, '192.168.3.11', 3306, 5, 'database', 'Ubuntu 20.04', 16, 64, 500, 'active', 'healthy', 28, '2024-01-15 11:00:00', 80),
            (5, '192.168.4.10', 6379, 7, 'cache', 'Redis 7.0', 2, 8, 50, 'active', 'healthy', 12, '2024-01-15 11:00:00', 100),
            (6, '192.168.5.10', 443, 8, 'storage', 'MinIO', 4, 32, 1000, 'maintenance', 'unknown', None, '2024-01-14 18:00:00', 0)
        ]
        
        self.conn.executemany("""
            INSERT INTO vip_member 
            (vip_id, member_address, port, zone_id, server_type, os_version, 
             cpu_cores, memory_gb, disk_gb, status, health_status, response_time_ms, last_check, weight) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, members_data)
        
        # Network Interfaces
        interfaces_data = [
            (1, 'eth0', '10.1.2.10', '255.255.255.0', 'management', 'up', 1000, 'full', 1500),
            (1, 'eth1', '10.1.0.10', '255.255.255.0', 'external', 'up', 10000, 'full', 1500),
            (1, 'eth2', '10.1.1.10', '255.255.255.0', 'internal', 'up', 10000, 'full', 1500),
            (2, 'eth0', '10.1.2.11', '255.255.255.0', 'management', 'up', 1000, 'full', 1500),
            (2, 'eth1', '10.1.0.11', '255.255.255.0', 'external', 'up', 10000, 'full', 1500),
            (2, 'eth2', '10.1.1.11', '255.255.255.0', 'internal', 'up', 10000, 'full', 1500),
            (3, 'eth0', '10.2.2.10', '255.255.255.0', 'management', 'up', 1000, 'full', 1500),
            (4, 'eth0', '10.3.2.10', '255.255.255.0', 'management', 'up', 1000, 'full', 1500),
            (5, 'eth0', '10.4.2.10', '255.255.255.0', 'management', 'down', 1000, 'full', 1500)
        ]
        
        self.conn.executemany("""
            INSERT INTO network_interfaces 
            (device_id, interface_name, ip_address, subnet_mask, interface_type, status, speed_mbps, duplex, mtu) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, interfaces_data)
        
        # SSL Certificates
        ssl_data = [
            ('www.company.com', 'DigiCert Inc', 'ABC12345678901234567', '2024-01-01', '2025-01-01', 2048, 'SHA256withRSA', 'active'),
            ('api.company.com', 'DigiCert Inc', 'DEF98765432109876543', '2024-01-01', '2025-01-01', 2048, 'SHA256withRSA', 'active'),
            ('admin.company.com', 'Let\'s Encrypt', 'GHI11111111111111111', '2024-01-01', '2024-04-01', 2048, 'SHA256withRSA', 'expiring'),
            ('storage.company.com', 'Internal CA', 'JKL22222222222222222', '2023-01-01', '2026-01-01', 4096, 'SHA256withRSA', 'active')
        ]
        
        self.conn.executemany("""
            INSERT INTO ssl_certificates 
            (common_name, issuer, serial_number, valid_from, valid_to, key_size, signature_algorithm, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ssl_data)
        
        # VIP SSL Bindings
        self.conn.executemany("""
            INSERT INTO vip_ssl_bindings (vip_id, cert_id, binding_order) 
            VALUES (?, ?, ?)
        """, [
            (2, 2, 1),  # api-backend uses api.company.com cert
            (3, 3, 1),  # admin-portal uses admin.company.com cert  
            (6, 4, 1)   # file-storage uses storage.company.com cert
        ])
        
        logger.info("Infrastructure sample data insertion completed")

        # DNS Zones
        self.conn.executemany("""
            INSERT INTO dns_zones 
            (zone_name, zone_type, primary_dns, secondary_dns, refresh_interval, retry_interval, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ('company.com', 'forward', '8.8.8.8', '8.8.4.4', 3600, 600, 'active'),
            ('api.company.com', 'forward', '1.1.1.1', '1.0.0.1', 1800, 300, 'active'),
            ('cdn.company.com', 'forward', '8.8.8.8', '8.8.4.4', 900, 180, 'active')
        ])
        
        # Geographic Regions
        self.conn.executemany("""
            INSERT INTO geo_regions (region_name, region_code, continent, country_codes, description) 
            VALUES (?, ?, ?, ?, ?)
        """, [
            ('North America', 'NA', 'North America', 'US,CA,MX', 'United States, Canada, Mexico'),
            ('Europe', 'EU', 'Europe', 'DE,FR,GB,IT,ES,NL', 'Major European countries'),
            ('Asia Pacific', 'APAC', 'Asia', 'SG,JP,AU,IN,CN', 'Asia Pacific region'),
            ('Latin America', 'LATAM', 'South America', 'BR,AR,CL,CO', 'Latin American countries'),
            ('Middle East', 'ME', 'Asia', 'AE,SA,IL', 'Middle East region')
        ])
        
        # Wide IPs (WIP)
        wip_data = [
            ('web-global', 'www.company.com', 'A', 300, 'cookie', 'topology', 'active', 30, '2024-01-15 08:00:00', 'Global web frontend'),
            ('api-global', 'api.company.com', 'A', 180, 'source_addr', 'ratio', 'active', 15, '2024-01-15 08:00:00', 'Global API endpoints'),
            ('cdn-global', 'cdn.company.com', 'CNAME', 600, 'none', 'geography', 'active', 60, '2024-01-15 08:00:00', 'Global CDN distribution'),
            ('admin-global', 'admin.company.com', 'A', 60, 'session', 'static_persist', 'active', 10, '2024-01-15 08:00:00', 'Global admin portal')
        ]
        
        self.conn.executemany("""
            INSERT INTO wip 
            (wip_name, domain_name, wip_type, ttl, persistence, load_balancing_method, 
             status, health_check_interval, created_date, description) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, wip_data)
        
        # WIP Pools
        wip_pools_data = [
            ('web-na-pool', 1, 'round_robin', 100, 2, 'active', 1, 'return_to_dns', '2024-01-15 08:00:00'),
            ('web-eu-pool', 1, 'least_connections', 90, 1, 'active', 1, 'return_to_dns', '2024-01-15 08:00:00'),
            ('web-apac-pool', 1, 'ratio', 80, 1, 'active', 1, 'return_to_dns', '2024-01-15 08:00:00'),
            ('api-na-pool', 2, 'topology', 100, 3, 'active', 1, 'fallback_ip', '2024-01-15 08:00:00'),
            ('api-eu-pool', 2, 'topology', 100, 2, 'active', 1, 'fallback_ip', '2024-01-15 08:00:00'),
            ('cdn-global-pool', 3, 'geography', 100, 1, 'active', 1, 'return_to_dns', '2024-01-15 08:00:00'),
            ('admin-secure-pool', 4, 'static_persist', 100, 5, 'active', 1, 'drop', '2024-01-15 08:00:00')
        ]
        
        self.conn.executemany("""
            INSERT INTO wip_pools 
            (pool_name, wip_id, load_balancing_method, priority, ratio, status, 
             health_check_enabled, fallback_mode, created_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, wip_pools_data)
        
        # WIP Pool Members
        wip_members_data = [
            # web-na-pool members (US East and West)
            (1, 1, 1, 1, 2, 100, 'active', 'healthy', 45, '2024-01-15 11:00:00', 1),
            (1, 2, 2, 2, 1, 90, 'active', 'healthy', 52, '2024-01-15 11:00:00', 1),
            
            # web-eu-pool members (EU Central)
            (2, 1, 3, 1, 1, 100, 'active', 'healthy', 38, '2024-01-15 11:00:00', 1),
            
            # web-apac-pool members (AP Southeast)
            (3, 1, 4, 1, 1, 100, 'active', 'degraded', 89, '2024-01-15 10:55:00', 1),
            
            # api-na-pool members
            (4, 2, 1, 1, 3, 100, 'active', 'healthy', 78, '2024-01-15 11:00:00', 1),
            (4, 2, 2, 2, 2, 90, 'active', 'healthy', 85, '2024-01-15 11:00:00', 1),
            
            # api-eu-pool members
            (5, 2, 3, 1, 2, 100, 'active', 'healthy', 67, '2024-01-15 11:00:00', 1),
            
            # cdn-global-pool members (all regions)
            (6, 6, 1, 1, 1, 100, 'active', 'unknown', None, '2024-01-14 18:00:00', 0),
            (6, 6, 2, 2, 1, 90, 'active', 'unknown', None, '2024-01-14 18:00:00', 0),
            (6, 6, 3, 3, 1, 80, 'active', 'unknown', None, '2024-01-14 18:00:00', 0),
            (6, 6, 4, 4, 1, 70, 'maintenance', 'unknown', None, '2024-01-14 18:00:00', 0),
            
            # admin-secure-pool members (limited to secure zones)
            (7, 3, 1, 1, 1, 100, 'active', 'healthy', 25, '2024-01-15 11:00:00', 1)
        ]
        
        self.conn.executemany("""
            INSERT INTO wip_pool_members 
            (pool_id, vip_id, dc_id, member_order, ratio, priority, status, 
             health_status, response_time_ms, last_health_check, enabled) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, wip_members_data)
        
        # WIP Geographic Routing Rules
        self.conn.executemany("""
            INSERT INTO wip_geo_routing (wip_id, region_id, pool_id, priority, enabled) 
            VALUES (?, ?, ?, ?, ?)
        """, [
            # Web global routing
            (1, 1, 1, 100, 1),  # NA -> web-na-pool
            (1, 2, 2, 100, 1),  # EU -> web-eu-pool  
            (1, 3, 3, 100, 1),  # APAC -> web-apac-pool
            (1, 4, 1, 80, 1),   # LATAM -> web-na-pool (fallback)
            (1, 5, 2, 80, 1),   # ME -> web-eu-pool (fallback)
            
            # API global routing
            (2, 1, 4, 100, 1),  # NA -> api-na-pool
            (2, 2, 5, 100, 1),  # EU -> api-eu-pool
            (2, 3, 4, 90, 1),   # APAC -> api-na-pool (fallback)
            
            # CDN uses single global pool
            (3, 1, 6, 100, 1),
            (3, 2, 6, 100, 1),
            (3, 3, 6, 100, 1),
            (3, 4, 6, 100, 1),
            (3, 5, 6, 100, 1),
            
            # Admin restricted to NA and EU only
            (4, 1, 7, 100, 1),
            (4, 2, 7, 90, 1)
        ])
    
    def create_views(self):
        """Create infrastructure-focused views."""
        
        # Infrastructure health summary
        self.conn.execute("""
            CREATE VIEW infrastructure_health AS
            SELECT 
                dc.dc_name,
                dc.region,
                lb.device_name,
                lb.model,
                lb.status AS lb_status,
                v.service_name,
                v.vip_address,
                v.port,
                v.protocol,
                COUNT(vm.member_id) AS total_members,
                SUM(CASE WHEN vm.health_status = 'healthy' THEN 1 ELSE 0 END) AS healthy_members,
                AVG(vm.response_time_ms) AS avg_response_time
            FROM datacenters dc
            JOIN load_balancer lb ON dc.dc_id = lb.dc_id
            JOIN vip_load_balancer vlb ON lb.device_id = vlb.device_id
            JOIN vip v ON vlb.vip_id = v.vip_id
            LEFT JOIN vip_member vm ON v.vip_id = vm.vip_id
            GROUP BY dc.dc_name, dc.region, lb.device_name, lb.model, lb.status, 
                     v.service_name, v.vip_address, v.port, v.protocol
        """)
        
        # SSL certificate expiry monitoring
        self.conn.execute("""
            CREATE VIEW ssl_expiry_report AS
            SELECT 
                ssl.common_name,
                ssl.issuer,
                ssl.valid_from,
                ssl.valid_to,
                ssl.status,
                CASE 
                    WHEN julianday(ssl.valid_to) - julianday('now') < 30 THEN 'Critical'
                    WHEN julianday(ssl.valid_to) - julianday('now') < 90 THEN 'Warning'
                    ELSE 'OK'
                END AS expiry_status,
                CAST(julianday(ssl.valid_to) - julianday('now') AS INTEGER) AS days_until_expiry,
                v.service_name,
                v.vip_address
            FROM ssl_certificates ssl
            LEFT JOIN vip_ssl_bindings vsb ON ssl.cert_id = vsb.cert_id
            LEFT JOIN vip v ON vsb.vip_id = v.vip_id
            ORDER BY days_until_expiry
        """)
        
        # Load balancer capacity analysis
        self.conn.execute("""
            CREATE VIEW lb_capacity_analysis AS
            SELECT 
                lb.device_name,
                lb.model,
                lb.cpu_cores,
                lb.memory_gb,
                lb.throughput_mbps,
                COUNT(DISTINCT vlb.vip_id) AS assigned_vips,
                COUNT(vm.member_id) AS total_backend_servers,
                SUM(CASE WHEN vm.status = 'active' THEN 1 ELSE 0 END) AS active_backend_servers,
                ROUND(AVG(vm.response_time_ms), 2) AS avg_backend_response_time
            FROM load_balancer lb
            LEFT JOIN vip_load_balancer vlb ON lb.device_id = vlb.device_id
            LEFT JOIN vip v ON vlb.vip_id = v.vip_id
            LEFT JOIN vip_member vm ON v.vip_id = vm.vip_id
            GROUP BY lb.device_id, lb.device_name, lb.model, lb.cpu_cores, lb.memory_gb, lb.throughput_mbps
        """)

        # WIP Performance Overview
        self.conn.execute("""
            CREATE VIEW wip_performance_overview AS
            SELECT 
                w.wip_name,
                w.domain_name,
                w.wip_type,
                w.load_balancing_method,
                w.status AS wip_status,
                COUNT(DISTINCT wp.pool_id) AS total_pools,
                COUNT(wpm.member_id) AS total_members,
                SUM(CASE WHEN wpm.status = 'active' AND wpm.enabled = 1 THEN 1 ELSE 0 END) AS active_members,
                SUM(CASE WHEN wpm.health_status = 'healthy' THEN 1 ELSE 0 END) AS healthy_members,
                ROUND(AVG(CASE WHEN wpm.health_status = 'healthy' THEN wpm.response_time_ms END), 2) AS avg_response_time,
                COUNT(DISTINCT wgr.region_id) AS geo_regions_configured
            FROM wip w
            LEFT JOIN wip_pools wp ON w.wip_id = wp.wip_id
            LEFT JOIN wip_pool_members wpm ON wp.pool_id = wpm.pool_id
            LEFT JOIN wip_geo_routing wgr ON w.wip_id = wgr.wip_id
            GROUP BY w.wip_id, w.wip_name, w.domain_name, w.wip_type, w.load_balancing_method, w.status
        """)
        
        # Geographic Distribution Analysis
        self.conn.execute("""
            CREATE VIEW wip_geographic_distribution AS
            SELECT 
                w.wip_name,
                w.domain_name,
                gr.region_name,
                gr.continent,
                wp.pool_name,
                wp.load_balancing_method,
                wgr.priority AS geo_priority,
                COUNT(wpm.member_id) AS pool_members,
                SUM(CASE WHEN wpm.health_status = 'healthy' THEN 1 ELSE 0 END) AS healthy_members,
                dc.dc_name,
                dc.country
            FROM wip w
            JOIN wip_geo_routing wgr ON w.wip_id = wgr.wip_id
            JOIN geo_regions gr ON wgr.region_id = gr.region_id
            JOIN wip_pools wp ON wgr.pool_id = wp.pool_id
            LEFT JOIN wip_pool_members wpm ON wp.pool_id = wpm.pool_id
            LEFT JOIN datacenters dc ON wpm.dc_id = dc.dc_id
            WHERE wgr.enabled = 1
            GROUP BY w.wip_name, w.domain_name, gr.region_name, gr.continent, 
                     wp.pool_name, wp.load_balancing_method, wgr.priority, dc.dc_name, dc.country
            ORDER BY w.wip_name, wgr.priority DESC
        """)
        
        # WIP Health Summary
        self.conn.execute("""
            CREATE VIEW wip_health_summary AS
            SELECT 
                w.domain_name,
                w.status AS wip_status,
                wp.pool_name,
                dc.dc_name AS datacenter,
                v.vip_address,
                v.service_name,
                wpm.health_status,
                wpm.response_time_ms,
                wpm.last_health_check,
                CASE 
                    WHEN wpm.last_health_check IS NULL THEN 'Never Checked'
                    WHEN datetime(wpm.last_health_check, '+' || w.health_check_interval || ' seconds') < datetime('now') THEN 'Overdue'
                    ELSE 'Current'
                END AS health_check_status
            FROM wip w
            JOIN wip_pools wp ON w.wip_id = wp.wip_id
            JOIN wip_pool_members wpm ON wp.pool_id = wpm.pool_id
            JOIN vip v ON wpm.vip_id = v.vip_id
            JOIN datacenters dc ON wpm.dc_id = dc.dc_id
            ORDER BY w.domain_name, wp.pool_name, dc.dc_name
        """)
    
    def get_database_stats(self):
        """Get statistics about the created database."""
        cursor = self.conn.cursor()
        
        # Get table names and row counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        stats = {"tables": {}}
        total_rows = 0
        
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            stats["tables"][table_name] = row_count
            total_rows += row_count
        
        stats["total_tables"] = len(tables)
        stats["total_rows"] = total_rows
        stats["database_path"] = self.db_path
        
        return stats
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def create_infrastructure_database(db_path: Optional[str] = None) -> str:
    """Create the infrastructure-focused database."""
    creator = InfrastructureDatabaseCreator(db_path)
    
    try:
        creator.create_all_tables()
        stats = creator.get_database_stats()
        
        print("✅ Infrastructure database created successfully!")
        print(f"📍 Location: {stats['database_path']}")
        print(f"📊 Tables: {stats['total_tables']}")
        print(f"📝 Total rows: {stats['total_rows']}")
        print("\n📋 Infrastructure table breakdown:")
        for table, rows in stats["tables"].items():
            print(f"   {table}: {rows} rows")
        
        return creator.db_path
        
    finally:
        creator.close()


if __name__ == "__main__":
    create_infrastructure_database()