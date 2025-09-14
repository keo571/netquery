# Sample Queries for Netquery Testing

This document provides comprehensive test queries organized by complexity and functionality to thoroughly test the Text-to-SQL pipeline. These queries match the evaluation framework in `scripts/evaluate_queries.py`.

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
- "List servers in us-east-1"

---

## 2. Aggregations

### Counting and Statistics
- "How many load balancers do we have?"
- "Count servers by datacenter"
- "What's the average CPU utilization by datacenter?"
- "What's the total bandwidth consumption?"
- "Show top 3 load balancers by traffic volume in each region"

---

## 3. Comparative Queries

### Performance Comparisons
- "Which servers have higher CPU than average?"
- "Find load balancers with more backends than typical"
- "Show datacenters with above-average server counts"

---

## 4. Multi-Table Joins

### Infrastructure Relationships
- "Show load balancers with their backend servers and current status"
- "List servers with their load balancer connections and roles"
- "Show load balancers with backend mappings and monitoring metrics"
- "Find servers with their monitoring data and SSL certificate status"
- "Show servers with their load balancers and SSL certificate details"

---

## 5. Set Operations & Existence

### Missing Data Analysis
- "Are there any servers without SSL certificates?"
- "Find load balancers with no backend servers assigned"
- "Show servers that have never been monitored"

---

## 6. Conditional Logic

### Dynamic Categorization
- "Categorize servers as High/Medium/Low based on CPU usage"
- "Show load balancers with traffic status (Heavy/Normal/Light)"
- "Display server health as Critical/Warning/OK based on metrics"

---

## 7. HAVING & Advanced Filters

### Group-Based Filtering
- "Show datacenters with more than 5 unhealthy servers"
- "Find load balancers where average response time exceeds 500ms"
- "List SSL providers managing more than 10 certificates"

---

## 8. Window Functions & Analytics

### Advanced Analytics
- "Rank servers by CPU utilization within each datacenter"
- "Compare each server's current CPU to its previous measurement"
- "Calculate moving average of response times over the last 5 measurements"

---

## 9. Time-Based Queries

### Time-Series Analysis
- "Show certificates expiring in the next 30 days"
- "Find servers with high CPU for the last 3 consecutive monitoring periods"
- "Show network traffic trends over the past week"

---

## 10. Troubleshooting

### Health and Status Checks
- "What's the health status by datacenter?"
- "Find servers with connection issues"

---

## 11. Performance Testing

### Large Dataset Queries
- "Show all monitoring metrics without any filtering"
- "Display comprehensive server details with all related data"

---

## 12. Subqueries & Advanced Patterns

### Complex Logic
- "Find servers in datacenters that have more than 5 load balancers"
- "Show load balancers with more backends than the average"
- "List servers that are monitored but not assigned to any load balancer"

---

## 13. String Operations & NULL Handling

### Text and Data Quality
- "Find servers with hostnames containing 'web'"
- "Show certificates with domains ending in '.com'"
- "Display servers where hostname is not recorded"
- "List load balancers with missing health score data"

---

## 14. Edge Cases

### Error Handling Tests
- "Show me nonexistent table data"
- "List servers in Mars datacenter"
- "Delete all servers" (should be blocked by safety validator)
- "Show me everything"
- "What's broken?"

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

### Data Volumes (from evaluate_queries.py)
- **Total Test Queries**: 49 across 14 categories
- **Infrastructure**: 50 records each (load_balancers, servers, ssl_certificates, vip_pools, backend_mappings)
- **Monitoring**: 840 network_traffic, 30 ssl_monitoring, 720 lb_health_log, 960 network_connectivity records