# Sample Queries for Testing Netquery

This document provides sample queries organized by functional categories to test the Text-to-SQL pipeline thoroughly, including network monitoring capabilities.

## 1. Basic Operations

### Infrastructure Overview
- "Show me all load balancers"
- "List all servers"  
- "What SSL certificates do we have?"
- "Display VIP pools"
- "Show me backend server mappings"

### Network Monitoring Overview
- "Show network traffic data"
- "List SSL certificate monitoring"
- "Display load balancer health logs"
- "Show network connectivity metrics"

## 2. Filtering & Conditions

### Status Filtering
- "Show me unhealthy load balancers"
- "List servers in maintenance"
- "Which certificates are expiring soon?"
- "Show load balancers with healthy backends"

### Location Filtering  
- "Show me load balancers in us-east-1"
- "List servers in eu-west-1 datacenter"
- "What infrastructure is in ap-southeast-1?"

### Performance Filtering
- "Show me servers with CPU usage above 80%"
- "Which servers have memory usage over 90%?"
- "List database servers that are unhealthy"
- "Show traffic with high error rates"
- "Find load balancers with response time over 50ms"

### Certificate Management
- "Which SSL certificates expire in the next 30 days?"
- "Show me expired certificates"
- "Find certificates from Let's Encrypt"
- "Show certificates expiring in 7 days"

### Network Performance Filtering
- "Show traffic with more than 1000 requests per second"
- "List connections with high latency"
- "Find servers with packet loss above 2%"
- "Show bandwidth utilization over 80%"

## 3. Analytics & Aggregations

### Counting and Statistics
- "How many load balancers do we have?"
- "Count unhealthy servers by datacenter"
- "What's the average CPU utilization by server role?"
- "Show me server count grouped by status"
- "What's the average response time by load balancer type?"
- "Show total requests per datacenter"

### Performance Analytics
- "What's the average memory usage by datacenter?"
- "Which datacenter has the highest CPU utilization?"
- "Show me load balancer distribution by type"
- "What's the average bandwidth usage by datacenter?"
- "Show error rate statistics by load balancer"

### Network Analytics
- "What's the average latency by datacenter?"
- "Show packet loss statistics by server role"  
- "What's the total bandwidth consumption?"
- "Show connection count averages by server"

## 4. Relationships & Joins

### Load Balancer Relationships
- "Show me load balancers with their backend servers"
- "List VIP pools with their load balancers"
- "Show me unhealthy load balancers and their backend servers"
- "Display load balancers with traffic metrics"

### Advanced Filtering with Joins
- "Show me healthy application load balancers in us-east-1"
- "List HTTPS VIP pools with unhealthy load balancers"  
- "Which servers are active backends for gateway load balancers?"
- "Show servers with their network connectivity status"

### Multi-Table Analytics
- "Show me load balancer backend server counts by datacenter"
- "List servers that are backends for multiple load balancers"
- "Which load balancers have the most VIP pools?"
- "Show servers with their traffic patterns"

## 5. Time-Based Operations

### Certificate Expiry
- "Which SSL certificates expire in the next 30 days?"
- "Show me certificates that expired in 2024"
- "List recently created certificates"

### Infrastructure Age
- "Show me load balancers created in the last month"
- "Which servers are oldest in each datacenter?"

### Monitoring Windows
- "Show traffic data from the past 3 days"
- "List SSL monitoring for the past week"
- "Show health logs from today"
- "Display connectivity metrics from yesterday"

## 6. Visualization & Charts

### Time-Series Line Charts (Trends Over Time)
- "Show network traffic for load balancer 1 over time"
- "Display bandwidth usage trends for the past week"
- "Show request rate patterns over time" 
- "List response time trends by load balancer"
- "Show error rate trends over time"
- "Show SSL certificate expiration trends"
- "Display certificate renewal patterns over time"
- "Show total certificate count over time"
- "List expired certificate trends"
- "Show backend health trends over time"
- "Display load balancer health scores over time"
- "Show request volume trends by load balancer"
- "List average response time trends"
- "Show network latency trends over time"
- "Display packet loss patterns by server"
- "Show uptime trends for servers"
- "List bandwidth utilization trends"
- "Show network traffic over time"
- "Display SSL certificate trends"  
- "Show load balancer health over time"
- "List server connectivity trends"

### Bar Charts (Comparisons & Distributions)
- "Show server performance by datacenter"
- "Display load balancer types distribution"
- "Show certificate status by provider"
- "List average response times by datacenter"
- "Show server count grouped by status"
- "Display load balancer distribution by type"
- "Show error rate statistics by load balancer"
- "List packet loss statistics by server role"

### Scatter Plots (Correlations & Relationships)
- "Show bandwidth vs request volume"
- "Display response time vs error rate"
- "Show CPU vs memory usage"
- "List latency vs packet loss correlation"

## 7. Troubleshooting & Diagnostics

### Health Overview
- "Show me all unhealthy infrastructure"
- "What's the health status by datacenter?"
- "List everything that needs attention"
- "Show load balancers with low health scores"

### Performance Issues
- "Which servers have the highest CPU utilization?"
- "Show me overloaded infrastructure"
- "Find performance bottlenecks by role"
- "List high-latency connections"
- "Show traffic with high error rates"

### Network Issues
- "Which servers have high packet loss?"
- "Show connections with poor uptime"
- "Find bandwidth bottlenecks"
- "List servers with connection issues"

### Security Auditing
- "Which SSL certificates need renewal?"
- "Show me certificates from untrusted issuers"
- "List expired certificates by domain"

## 8. Edge Cases & Testing

### Invalid Queries (should handle gracefully)
- "Show me nonexistent table data"
- "List servers in Mars datacenter"  
- "Delete all servers" (should be blocked by safety validator)

### Ambiguous Queries
- "Show me everything"
- "What's broken?"
- "Give me a summary"

---

## Quick Test Commands

```bash
# Basic operations
python gemini_cli.py "Show me all load balancers"
python gemini_cli.py "List unhealthy servers"
python gemini_cli.py "Show network traffic data"

# Filtering & conditions
python gemini_cli.py "Show me load balancers in us-east-1"
python gemini_cli.py "Which certificates expire in 30 days?"

# Analytics & aggregations
python gemini_cli.py "What's the average CPU utilization by datacenter?"
python gemini_cli.py "Count unhealthy servers by datacenter"

# Visualization queries
python gemini_cli.py "Show network traffic trends over time"
python gemini_cli.py "Display SSL certificate monitoring trends"
python gemini_cli.py "Show server performance by datacenter"

# With analysis  
python gemini_cli.py "Show me load balancers in us-east-1" --reasoning

# With exports
python gemini_cli.py "What's the average CPU utilization by datacenter?" --csv
python gemini_cli.py "Show network traffic patterns" --html

# Full featured
python gemini_cli.py "Show load balancer health trends" --reasoning --csv --html
```

---

## Database Schema Quick Reference

### **Core Infrastructure Tables**

#### **load_balancers**
- **Columns**: id, name, status, vip_address, datacenter, lb_type, algorithm, created_at
- **Status**: healthy, unhealthy, maintenance, draining
- **Types**: application, network, gateway, internal
- **Datacenters**: us-east-1, us-west-2, eu-west-1, ap-southeast-1

#### **servers** 
- **Columns**: id, hostname, status, cpu_utilization, memory_usage, datacenter, role, created_at
- **Roles**: web, api, database, cache, worker, proxy

#### **ssl_certificates**
- **Columns**: id, domain, issuer, expiry_date, status, provider, created_at
- **Providers**: DigiCert, GlobalSign, Let's Encrypt, Cloudflare, AWS

#### **vip_pools** (Links VIPs to load balancers)
- **Columns**: id, vip_address, port, protocol, load_balancer_id, created_at

#### **backend_mappings** (Links servers to load balancers) 
- **Columns**: id, load_balancer_id, server_id, weight, active, created_at

### **Network Monitoring Tables (Time-Series Data)**

#### **network_traffic** 
- **Columns**: id, load_balancer_id, timestamp, requests_per_second, response_time_ms, bandwidth_mbps, active_connections, error_rate_percent
- **Records**: 840 (7 days × 24 hours × 5 load balancers)
- **Perfect for**: Line charts showing traffic patterns over time

#### **ssl_monitoring**
- **Columns**: id, date, certificates_expiring_30days, certificates_expiring_7days, total_certificates, expired_certificates, renewed_certificates  
- **Records**: 30 (30 days of SSL health data)
- **Perfect for**: Line charts showing certificate lifecycle trends

#### **lb_health_log**
- **Columns**: id, load_balancer_id, timestamp, healthy_backends, total_backends, avg_response_time_ms, total_requests, health_score_percent
- **Records**: 720 (3 days × 24 hours × 10 load balancers)
- **Perfect for**: Line charts showing load balancer health over time

#### **network_connectivity**
- **Columns**: id, server_id, timestamp, latency_ms, packet_loss_percent, uptime_percent, bandwidth_utilization_percent, connection_count
- **Records**: 960 (2 days × 24 hours × 20 servers)  
- **Perfect for**: Line charts showing network performance trends

---

## Organization Benefits

This new structure provides several advantages:

1. **Functional Grouping**: Queries are organized by what they accomplish, not just complexity
2. **Progressive Learning**: Each section builds on concepts from previous sections  
3. **Consolidated Charts**: All visualization queries are grouped in section 6 for easy reference
4. **Clear Purpose**: Each query category has a specific testing or operational purpose
5. **Better Navigation**: Numbered sections make it easier to reference specific query types

### Chart-Ready Data Summary

- **📈 Line Charts**: Network traffic, SSL trends, health metrics, connectivity patterns
- **📊 Bar Charts**: Performance by location, status distributions, provider comparisons  
- **🎯 Scatter Plots**: Performance correlations, capacity relationships
- **🥧 Pie Charts**: Status breakdowns, type distributions, provider shares

*This reorganized query list maintains comprehensive coverage while providing better logical flow and consolidated chart-generation capabilities.*