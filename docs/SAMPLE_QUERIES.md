# Sample Queries

This guide provides comprehensive query examples for both **dev mode (SQLite)** and **prod mode (PostgreSQL)** datasets.

## Dataset Overview

### Dev Mode (SQLite)
The dev profile uses SQLite with synthetic load balancer data (see [scripts/create_data_sqlite.py](../scripts/create_data_sqlite.py)):

**Tables**:
- `load_balancers` - Load balancer instances with VIP addresses
- `servers` - Backend servers with CPU/memory metrics
- `ssl_certificates` - SSL/TLS certificates with expiry tracking
- `vip_pools` - Virtual IP pools with protocol configuration
- `backend_mappings` - Load balancer to server mappings
- `network_traffic` - Traffic metrics (requests/sec, bandwidth, latency)
- `ssl_monitoring` - Daily SSL certificate monitoring aggregates
- `lb_health_log` - Load balancer health scores over time
- `network_connectivity` - Server connectivity metrics (latency, packet loss)

**Scale**: ~50 load balancers, ~50 servers across 4 datacenters (us-east-1, us-west-2, eu-west-1, ap-southeast-1)

### Prod Mode (PostgreSQL)
The prod profile uses PostgreSQL with a schema from Excel (see [scripts/create_data_postgres.py](../scripts/create_data_postgres.py)):

**Tables**:
- `load_balancers` - Load balancer instances
- `virtual_ips` - Virtual IP endpoints
- `wide_ips` - Global DNS load balancing (wide IPs)
- `wide_ip_pools` - Pools of virtual IPs for wide IPs
- `backend_servers` - Backend server instances
- `traffic_stats` - Per-VIP traffic statistics

**Scale**: 20-100 rows per table, supports global DNS routing and wide IP configurations

## Running Queries

**Dev Mode (SQLite)**:
```bash
python gemini_cli.py "your question here"
# or explicitly:
NETQUERY_ENV=dev python gemini_cli.py "your question here"
```

**Prod Mode (PostgreSQL)**:
```bash
NETQUERY_ENV=prod python gemini_cli.py "your question here"
```

---

## Basic Queries

### Inventory & Status

**Dev Mode**:
- "Show all load balancers and their current status"
- "List all servers in us-east-1"
- "Which load balancers have status 'healthy'?"
- "Show the 10 most recently created load balancers"
- "List all load balancers with their VIP addresses and datacenters"

**Prod Mode**:
- "Show all load balancers and their datacenters"
- "List all virtual IPs with their IP addresses and ports"
- "Which backend servers are in us-west-2?"
- "Show the most recently created load balancers"
- "List all wide IPs with their DNS configurations"

### Health & Availability

**Dev Mode**:
- "Which servers have status 'unhealthy'?"
- "Show load balancers with health score below 80"
- "List all servers with CPU utilization above 90%"
- "Which servers have high memory usage above 85%?"
- "Show servers in maintenance or draining status"

**Prod Mode**:
- "Which backend servers have status 'unhealthy'?"
- "Show load balancers with status 'maintenance'"
- "List all backend servers and their current status"
- "Which load balancers are active?"

---

## Relationship Queries

### Load Balancer to Server Mappings

**Dev Mode**:
- "For each load balancer, show its backend servers"
- "Show all servers mapped to load balancers in us-east-1"
- "Which load balancers have more than 5 backend servers?"
- "List backend mappings with their health check paths and weights"
- "Show the server distribution across all load balancers by datacenter"

**Prod Mode**:
- "For each load balancer, list its backend servers with their status"
- "Show which backend servers belong to each load balancer"
- "List all load balancer and backend server relationships"
- "Which load balancers have the most backend servers?"

### VIP and Pool Relationships

**Dev Mode**:
- "Show all VIP pools with their load balancers"
- "List VIP pools grouped by protocol"
- "Which VIP addresses are on port 443?"
- "Show VIP pools with their associated load balancer names"

**Prod Mode**:
- "Show each virtual IP with its load balancer"
- "List all virtual IPs and their protocols"
- "For each wide IP, show its virtual IP pool members"
- "Which wide IP pools have the most virtual IP members?"
- "Show the complete hierarchy from wide IPs to virtual IPs to load balancers"

### SSL Certificates (Dev Only)

**Dev Mode**:
- "Which SSL certificates are expiring in the next 30 days?"
- "Show all SSL certificates with status 'expired'"
- "List certificates from Let's Encrypt"
- "Which domains have active SSL certificates?"
- "Show certificates expiring in the next 7 days"

---

## Aggregations & Analytics

### Traffic Analysis

**Dev Mode**:
- "What's the average requests per second for each load balancer?"
- "Show total bandwidth by datacenter"
- "Which load balancer has the highest average response time?"
- "Calculate average error rate by load balancer"
- "Show peak active connections for each load balancer"
- "What's the average bandwidth utilization across all load balancers?"

**Prod Mode**:
- "Show total traffic by load balancer"
- "Calculate average requests per second by datacenter"
- "Which virtual IPs have the highest traffic?"
- "Show total bytes transferred per load balancer"
- "What's the average connection count per virtual IP?"

### Resource Distribution

**Dev Mode**:
- "Count servers per datacenter"
- "How many load balancers are in each datacenter?"
- "Show the distribution of load balancer types"
- "What's the average number of backend servers per load balancer?"
- "Count VIP pools by protocol"
- "Show server distribution by role (web, api, database, etc.)"

**Prod Mode**:
- "Count load balancers per datacenter"
- "How many backend servers does each load balancer have?"
- "Show the distribution of load balancer types"
- "Count virtual IPs per load balancer"
- "How many wide IPs are configured?"

---

## Time-Series Queries

### Network Traffic Trends

**Dev Mode**:
- "Show network traffic for the past 24 hours"
- "Which load balancer had the highest traffic spike in the last 7 days?"
- "Show hourly average requests per second for load balancer id 1"
- "Compare bandwidth usage between yesterday and today"
- "Show traffic patterns for the past week grouped by hour of day"
- "Which times of day have the highest error rates?"

**Prod Mode**:
- "Show traffic stats over time for load balancer 1"
- "Which virtual IPs had the most traffic in the last day?"
- "Show traffic trends for the past week"
- "Compare traffic between different time periods"

### Health Monitoring

**Dev Mode**:
- "Show health score trends for load balancer id 1 over the last 3 days"
- "List all load balancers with declining health scores"
- "Which load balancers had health scores below 75% in the past day?"
- "Show the ratio of healthy to total backends over time"
- "Track average response times for load balancers over the past week"
- "Which load balancers have the most variable health scores?"

**Prod Mode**:
- "Show backend server status changes over time"
- "Which backend servers have had status changes recently?"
- "Track load balancer availability over time"

### SSL Monitoring (Dev Only)

**Dev Mode**:
- "Show daily SSL monitoring stats for the past 30 days"
- "How many certificates expired in the last week?"
- "Track certificates expiring in 30 days over time"
- "Show the trend of certificate renewals"
- "Which days had the most certificates expiring soon?"

### Network Connectivity (Dev Only)

**Dev Mode**:
- "Show network latency trends for servers in us-east-1"
- "Which servers had packet loss above 1% in the past 2 days?"
- "Track uptime percentage for all servers over time"
- "Show servers with the highest bandwidth utilization"
- "Which servers had connectivity issues (high latency or packet loss)?"
- "Compare network performance across datacenters"

---

## Advanced Queries

### Performance Optimization

**Dev Mode**:
- "Which load balancers have high response time and high error rates?"
- "Show servers with high CPU and high memory usage"
- "Find load balancers with imbalanced backend weights"
- "Which servers have poor network connectivity (high latency and packet loss)?"
- "Show correlation between server health and network traffic"
- "Identify load balancers with many unhealthy backends"

**Prod Mode**:
- "Which load balancers have the most unhealthy backend servers?"
- "Show virtual IPs with high traffic but many unhealthy backends"
- "Identify load balancers that might need more capacity"

### Capacity Planning

**Dev Mode**:
- "Which datacenters have the highest server utilization (CPU + memory)?"
- "Show load balancers that might need additional backend servers"
- "Calculate average traffic per server by datacenter"
- "Identify underutilized servers (low CPU and low traffic)"
- "Which datacenters have the most servers in maintenance?"
- "Show load balancers with high traffic but few backends"

**Prod Mode**:
- "Which datacenters have the most load balancers?"
- "Show the backend server to load balancer ratio by datacenter"
- "Identify load balancers that could be consolidated"
- "Which wide IPs have the most virtual IP members?"

### Complex Joins

**Dev Mode**:
- "Show load balancers with their servers, VIP pools, and health scores"
- "List all SSL certificates with their associated VIP configurations"
- "Show comprehensive health view: load balancers, backends, network connectivity, and traffic"
- "Compare traffic metrics with health scores for all load balancers"
- "Show servers with their load balancers, roles, and network connectivity stats"

**Prod Mode**:
- "Show the complete path from wide IP to backend servers"
- "List all traffic statistics with their virtual IPs and load balancers"
- "Show the full hierarchy of global load balancing configuration"
- "Display all relationships: load balancers → virtual IPs → wide IPs → wide IP pools"

---

## Tips for Writing Good Queries

### Be Specific About Timeframes
- **Good**: "Show network traffic in the last 24 hours"
- **Bad**: "Show network traffic" (may return too much data)

### Specify What You Want to See
- **Good**: "List load balancers with their datacenter, status, and VIP address"
- **Bad**: "Show load balancers" (may miss important fields)

### Use Natural Language
- **Good**: "Which servers are unhealthy in us-east-1?"
- **Also Good**: "Show me all servers in us-east-1 that have status not equal to healthy"

### Ask for Analysis, Not Just Data
- **Good**: "What's the average requests per second by datacenter?"
- **Less Useful**: "Show all network traffic records" (requires manual calculation)

### Leverage Relationships
- **Good**: "For each load balancer, show its backend servers and their health status"
- **Less Useful**: Asking for load balancers and servers separately (requires manual joining)

### Use Appropriate Filters
- **Good**: "Show servers with CPU above 80% in us-east-1"
- **Good**: "List load balancers created in the last 30 days"

---

## Differences Between Dev and Prod

| Feature | Dev (SQLite) | Prod (PostgreSQL) |
|---------|--------------|-------------------|
| **Complexity** | More tables, detailed monitoring | Simpler schema focused on core LB features |
| **Scale** | ~50 records per table | 20-100 records per table (randomized) |
| **SSL** | Full SSL certificate management | Not included |
| **Global LB** | Not supported | Wide IP support for global DNS routing |
| **Traffic Metrics** | `network_traffic` (time-series) | `traffic_stats` (per-VIP aggregates) |
| **Health Monitoring** | `lb_health_log` with scores | Status fields only |
| **Network Monitoring** | `network_connectivity` detailed | Not included |
| **Servers** | `servers` table with metrics | `backend_servers` table (simpler) |
| **VIPs** | `vip_pools` linked to LBs | `virtual_ips` as separate entities |
| **Use Case** | Development, detailed monitoring, SSL management | Production schema validation, global routing |

### When to Use Each Mode

**Use Dev Mode for**:
- Learning the system with comprehensive data
- Testing queries with time-series data
- SSL certificate management and monitoring
- Network connectivity analysis
- Detailed health score tracking
- Server resource utilization queries

**Use Prod Mode for**:
- Testing against production-like schema structure
- Global load balancing with wide IPs
- Validating schema from Excel definitions
- Simpler load balancer-to-backend relationships
- Wide IP pool configurations

---

## Query Export Options

All queries support export flags:

```bash
# Export to HTML table
python gemini_cli.py "Show all load balancers" --html

# Export to CSV file
python gemini_cli.py "Show traffic stats" --csv

# Show SQL explanation
python gemini_cli.py "Show servers" --explain
```

Exported files are saved to `query_exports/` directory.

---

## Next Steps

1. **Try the queries**: Copy any query above and run it with `gemini_cli.py`
2. **Modify and experiment**: Change datacenters, time ranges, or thresholds
3. **Combine filters**: "Show unhealthy servers in us-east-1 with CPU above 80%"
4. **Export results**: Add `--html` or `--csv` to save results
5. **View SQL**: Add `--explain` to understand how queries are translated

For more information:
- Architecture: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- Getting Started: [docs/GETTING_STARTED.md](GETTING_STARTED.md)
- Schema Details: [docs/SCHEMA_INGESTION.md](SCHEMA_INGESTION.md)
