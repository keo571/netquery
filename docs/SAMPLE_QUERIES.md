# Sample Queries for Netquery Testing

This document provides comprehensive test queries organized by complexity and functionality to thoroughly test the Text-to-SQL pipeline.

## Database Schema Quick Reference

### Core Infrastructure Tables
- **load_balancers**: id, name, status, vip_address, datacenter, lb_type, algorithm, created_at
- **servers**: id, hostname, status, cpu_utilization, memory_usage, datacenter, role, created_at  
- **ssl_certificates**: id, domain, issuer, expiry_date, status, provider, created_at
- **vip_pools**: id, vip_address, port, protocol, load_balancer_id, created_at
- **backend_mappings**: id, load_balancer_id, server_id, weight, health_check_path, created_at

### Monitoring Tables (Time-Series Data)
- **network_traffic**: id, load_balancer_id, timestamp, requests_per_second, response_time_ms, bandwidth_mbps, active_connections, error_rate_percent
- **ssl_monitoring**: id, date, certificates_expiring_30days, certificates_expiring_7days, total_certificates, expired_certificates, renewed_certificates
- **lb_health_log**: id, load_balancer_id, timestamp, healthy_backends, total_backends, avg_response_time_ms, total_requests, health_score_percent
- **network_connectivity**: id, server_id, timestamp, latency_ms, packet_loss_percent, uptime_percent, bandwidth_utilization_percent, connection_count

---

## 1. Basic Queries

### Simple Table Queries
- "Show me all load balancers"
- "List all servers"
- "What SSL certificates do we have?"
- "Display VIP pools"
- "Show backend mappings"

### Basic Filtering
- "Show unhealthy load balancers"
- "List servers in maintenance"
- "Find expired SSL certificates"
- "Show servers with high CPU usage"
- "List load balancers in us-east-1"

---

## 2. Analytics & Aggregations

### Counting and Statistics
- "How many load balancers do we have?"
- "Count servers by datacenter"
- "What's the average CPU utilization by datacenter?"
- "Show server count grouped by status"
- "Count SSL certificates by provider"

### Performance Metrics
- "What's the average memory usage by server role?"
- "Show load balancer distribution by type"
- "Calculate average response time by datacenter"
- "Show error rate statistics by load balancer"
- "What's the total bandwidth consumption?"

---

## 3. Multi-Table Joins

### Infrastructure Relationships
- "Show load balancers with their backend servers and current status"
- "List servers with their load balancer connections and roles"
- "Find load balancers with their VIP pool configurations"
- "Show backend mappings with server and load balancer details"
- "Display VIP pools with their load balancer information"

### Complex Filtering with Joins
- "Show unhealthy load balancers in us-east-1 with their backend servers that have high CPU usage"
- "Find HTTPS VIP pools connected to application load balancers"
- "List servers that are backends for unhealthy load balancers and have high memory usage"
- "Show SSL certificates expiring in the next 30 days with their status"

### Network Performance Analysis
- "Show servers with high packet loss and their network connectivity details"
- "List load balancers with their VIP pools and average traffic statistics"
- "Find servers with low uptime and their load balancer associations"
- "Show network connectivity patterns for database servers"
- "List load balancers with response times above 100ms and their backend servers"

---

## 4. Time-Series and Visualization Queries

### Time-Series Analysis (Line Charts)
- "Show network traffic trends over time"
- "Display bandwidth usage patterns for the past week"
- "Show backend health trends over time"
- "Display load balancer health scores over time"
- "Show network latency trends over time"
- "List server connectivity trends"

### Comparative Analysis (Bar Charts)
- "Show server performance by datacenter"
- "Display load balancer types distribution"
- "Show certificate status by provider"
- "List average response times by datacenter"
- "Count servers by status and datacenter"

### Correlation Analysis (Scatter Plots)
- "Show CPU vs memory usage"
- "Display response time vs error rate"
- "Show bandwidth vs request volume"
- "List latency vs packet loss correlation"

---

## 5. Troubleshooting Queries

### Current Status Checks
- "Show certificates expiring in the next 30 days"
- "List current SSL monitoring status"
- "Display current network connectivity metrics"
- "Show recent load balancer health logs"

### Health Issues
- "Show all unhealthy infrastructure"
- "What's the health status by datacenter?"
- "Find servers with connection issues"

### Performance Problems
- "Which servers have the highest CPU utilization?"
- "Find performance bottlenecks by role"
- "List high-latency connections"

### Security Auditing
- "Which SSL certificates need renewal?"
- "Show expired certificates by domain"

---

## 6. Test Commands by Category

### Basic Operations
```bash
python gemini_cli.py "Show me all load balancers"
```

### Analytics
```bash
python gemini_cli.py "What's the average CPU utilization by datacenter?"
```

### Complex Joins (Tested & Working)
```bash
python gemini_cli.py "Show load balancers with their backend servers and current status"
```

### Export Features (One Example per Flag)
```bash
python gemini_cli.py "Show server performance by datacenter" --html
python gemini_cli.py "Show network traffic over time" --csv
python gemini_cli.py "List load balancer health trends" --explain
python gemini_cli.py "Show comprehensive report" --html --csv --explain
```

---

## 7. Edge Cases & Error Handling

### Invalid Queries (Should Handle Gracefully)
- "Show me nonexistent table data"
- "List servers in Mars datacenter"
- "Delete all servers" (should be blocked by safety validator)

### Ambiguous Queries
- "Show me everything"
- "What's broken?"
- "Give me a summary"

---

## 8. Performance Testing

### Large Result Sets
```bash
python gemini_cli.py "Show all network traffic data with load balancer details"
```

### Complex Aggregations
```bash
python gemini_cli.py "Calculate average response time and error rate by load balancer type"
```

---

## Quick Reference Values

### Status Values
- **Server/LB Status**: healthy, unhealthy, maintenance, draining
- **SSL Status**: active, expired
- **Datacenters**: us-east-1, us-west-2, eu-west-1, ap-southeast-1

### Types and Roles
- **LB Types**: application, network, gateway, internal
- **Server Roles**: web, api, database, cache, worker, proxy
- **Protocols**: HTTP, HTTPS, TCP, UDP, GRPC
- **SSL Providers**: DigiCert, GlobalSign, Let's Encrypt, Cloudflare, AWS

### Data Volumes
- **Infrastructure**: 50 records each (load_balancers, servers, ssl_certificates, vip_pools, backend_mappings)
- **Monitoring**: 840 network_traffic, 30 ssl_monitoring, 720 lb_health_log, 960 network_connectivity records