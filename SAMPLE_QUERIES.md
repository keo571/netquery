# Sample Queries for Testing Netquery

This document provides sample queries organized by complexity level to test the Text-to-SQL pipeline thoroughly.

## Basic Queries (Simple SELECT operations)

### Load Balancers
- "Show me all load balancers"
- "List all load balancers"
- "What load balancers do we have?"
- "Display load balancer information"

### Servers
- "Show me all servers"
- "List all servers"
- "What servers are available?"
- "Display server information"

### SSL Certificates
- "Show me all SSL certificates"
- "List all certificates"
- "What certificates do we have?"
- "Display certificate information"

## Intermediate Queries (Filtering and conditions)

### Status-based filtering
- "Show me load balancers with unhealthy status"
- "List all servers with healthy status"  
- "Which load balancers are in maintenance status?"
- "Show me servers that have unhealthy status"
- "Find load balancers with healthy status"

### Location-based filtering
- "Show me load balancers in us-east-1"
- "List servers in eu-west-1 datacenter"
- "What load balancers are in the us-west-2 region?"
- "Show me all infrastructure in the production datacenter"

### SSL Certificate status
- "Which SSL certificates have already expired?"
- "Show me certificates that expire in the next 30 days"
- "List certificates that expire in the next year"
- "Find certificates from Let's Encrypt"
- "Show me expired SSL certificates"
- "Which certificates are expiring soon?"

### Server roles
- "Show me all web servers"
- "List database servers that are unhealthy"
- "Which cache servers have high memory usage?"
- "Show me worker servers in us-west-2"
- "List API servers with CPU usage above 80%"
- "Which proxy servers are in maintenance?"

### Performance metrics
- "Show me servers with high CPU utilization"
- "List servers with CPU usage above 80%"
- "Which servers have memory usage over 90%?"
- "Show me servers with low resource usage"
- "What's the average CPU usage for web servers?"
- "List database servers with memory usage below 50%"

## Advanced Queries (Aggregations and calculations)

### Counting and statistics
- "How many load balancers do we have?"
- "Count the number of unhealthy servers"
- "What's the total number of SSL certificates?"
- "How many servers are in each datacenter?"

### Averages and metrics
- "What's the average CPU utilization across all servers?"
- "Show me the average memory usage by datacenter"
- "What's the mean CPU usage for healthy servers?"
- "Calculate average resource utilization"

### Grouping operations
- "Show me server count by datacenter"
- "Group load balancers by status"
- "Count servers by their role"
- "Summarize certificate count by issuer"

## Complex Queries (Multiple tables and relationships)

### Cross-table relationships
- "Show me load balancers and their backend servers"
- "List VIP pools with their associated load balancers"
- "Which servers are mapped to which load balancers?"
- "Show me the relationship between VIPs and load balancers"

### Load balancer types and algorithms
- "Show me application load balancers using round robin algorithm"
- "List network load balancers that are unhealthy"
- "Which gateway load balancers use least connections?"
- "Show me internal load balancers with weighted algorithm"

### VIP pools and protocols  
- "Show me all HTTPS VIP pools with their load balancers"
- "List TCP VIP pools on port 80"
- "Which load balancers have GRPC VIP pools?"
- "Show me VIP addresses grouped by protocol"

### Backend server mappings
- "Show me servers that are active backends for load balancers"
- "List inactive backend mappings"
- "Which servers have the highest weight in backend pools?"
- "Show me load balancers with their backend server counts"

### Complex filtering with joins
- "Show me unhealthy load balancers and their backend servers"
- "List servers that are backends for healthy load balancers"  
- "Which VIP addresses belong to application load balancers in us-east-1?"
- "Show me load balancers with their VIP pools and backend servers"

### Multi-condition queries
- "Show me healthy application load balancers in us-east-1 with round robin algorithm"
- "List web servers with high CPU usage that are active backends"
- "Find maintenance load balancers with their HTTPS VIP pools"
- "Show me database servers that are backends for internal load balancers"

## Time-based Queries

### Date filtering
- "Which SSL certificates expire in the next 30 days?"
- "Show me certificates that expire this year"
- "List certificates created in the last month"
- "Which certificates expired in 2024?"

### Recent activity
- "Show me recently created load balancers"
- "List servers added in the last week"
- "What infrastructure was created today?"

## Troubleshooting Queries

### Health monitoring
- "Show me all unhealthy infrastructure"
- "List any load balancers or servers that are down"
- "What's the health status of our infrastructure?"
- "Show me everything that needs attention"

### Performance issues
- "Which servers have the highest CPU utilization?"
- "Show me servers with resource problems"
- "List load balancers that might be overloaded"
- "Find infrastructure with performance issues"

### Security concerns  
- "Which SSL certificates need to be renewed?"
- "Show me expired or expiring certificates"
- "List certificates from untrusted providers"
- "Find security issues with our certificates"

## Edge Cases and Error Testing

### Invalid queries (should handle gracefully)
- "Show me nonexistent table data"
- "List servers in Mars datacenter"
- "What's the color of our load balancers?"
- "Delete all servers" (should be blocked by safety validator)

### Ambiguous queries
- "Show me everything"
- "What's broken?"
- "Give me a summary"
- "List all problems"

## Usage Examples

### Command Line Testing
```bash
# Basic query
python gemini_cli.py "Show me all load balancers"

# Intermediate query  
python gemini_cli.py "Show me unhealthy servers in us-east-1"

# Advanced query
python gemini_cli.py "What's the average CPU utilization by datacenter?"

# Complex query
python gemini_cli.py "Show me load balancers with their VIP pools and backend servers"
```

### Expected Outputs

**Simple Query**: Clean table with all requested data
**Filtered Query**: Subset of data meeting the criteria
**Aggregated Query**: Summary statistics and calculations
**Complex Query**: Multi-table results with relationships
**Error Cases**: User-friendly error messages with suggestions

## Tips for Testing

1. **Start Simple**: Begin with basic queries to ensure core functionality works
2. **Add Complexity**: Gradually increase query complexity to test different pipeline components
3. **Test Edge Cases**: Try invalid queries to ensure proper error handling
4. **Vary Phrasing**: Use different ways to ask the same question
5. **Check Performance**: Monitor response times for complex queries
6. **Verify Accuracy**: Cross-check results with direct SQL queries when needed

## Database Schema Reference

The test database contains these tables with relationships:

### **load_balancers** 
- **id** (Primary Key), **name**, **status**, **vip_address**, **datacenter**, **lb_type**, **algorithm**, **created_at**
- Status values: healthy, unhealthy, maintenance, draining
- Types: application, network, gateway, internal  
- Algorithms: round_robin, least_connections, ip_hash, weighted
- Datacenters: us-east-1, us-west-2, eu-west-1, ap-southeast-1

### **servers**
- **id** (Primary Key), **hostname**, **status**, **cpu_utilization**, **memory_usage**, **datacenter**, **role**, **created_at**
- Status values: healthy, unhealthy, maintenance, draining
- Roles: web, api, database, cache, worker, proxy
- CPU/Memory: Float values (0-100 representing percentages)

### **ssl_certificates**
- **id** (Primary Key), **domain**, **issuer**, **expiry_date**, **status**, **provider**, **created_at**  
- Status values: valid, expiring_soon, expired, revoked
- Providers: DigiCert, GlobalSign, Let's Encrypt, Cloudflare, AWS

### **vip_pools** (Junction table)
- **id** (Primary Key), **vip_address**, **port**, **protocol**, **load_balancer_id** (FK), **created_at**
- Protocols: HTTP, HTTPS, TCP, UDP, GRPC
- Links VIP addresses to load balancers

### **backend_mappings** (Junction table)  
- **id** (Primary Key), **load_balancer_id** (FK), **server_id** (FK), **weight**, **active**, **created_at**
- Maps servers to load balancers with load balancing weights
- Active: 1 (active) or 0 (inactive)

## Relationships
- **Load Balancers** ←→ **VIP Pools** (one-to-many)
- **Load Balancers** ←→ **Backend Mappings** ←→ **Servers** (many-to-many)

This gives you a comprehensive test suite covering all aspects of your Text-to-SQL pipeline with realistic network infrastructure relationships!