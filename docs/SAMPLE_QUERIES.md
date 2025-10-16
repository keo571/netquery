# Sample Queries for Load Balancer Dataset

The production profile seeds PostgreSQL with synthetic data derived from `schema_files/load_balancer_schema.xlsx` (see `setup/create_data_postgres.py`). The generator populates:

- `load_balancers`, `virtual_ips`, `wide_ips`, `wide_ip_pools`, `backend_servers`, `traffic_stats`
- Randomized datacenters, statuses (`active`, `healthy`, `unhealthy`, `maintenance`), DNS algorithms (`round_robin`, `least_connections`, `ip_hash`)
- Per-VIP traffic metrics (requests_per_second, bytes_in/out, active_connections)

Use the prompts below with `NETQUERY_ENV=prod python gemini_cli.py "<question>"` (after `setup/ingest_schema.py build --output schema_files/prod_schema.json`).

## Inventory & Filtering
- "Show the ten most recently added load balancers and which datacenter each runs in, including their current status." 
- "Which backend servers in us-east-1 are currently failing health checks, and which load balancer routes traffic to them?" 
- "List virtual IP endpoints that rely on the least-connections policy, together with the pool name and load balancer handling them." 
- "Which global wide IP domains are disabled right now, and what TTL and load-balancing method do they use?" 

## Relationship-Focused Queries
- "For every load balancer, list its backend servers with hostnames and current health state." 
- "Show each virtual IP alongside its load balancer and any wide IP domains that reference it." 
- "For each wide IP, list the virtual IP members, noting their traffic priority, weight, and whether the member is active." 
- "Which virtual IPs appear in more than one wide IP pool, and how many pools reference each one?" 

## Aggregations & Summaries
- "Count load balancers per datacenter and include how many backend servers each site supports." 
- "Summarize inbound and outbound traffic totals per datacenter by linking traffic statistics to virtual IPs and load balancers." 
- "What is the average request rate per protocol during the last 30 days?" 
- "Which virtual IPs recorded the highest peak connection counts in the past week?" 

## Time-Series & Diagnostics
- "Show the hourly average request rate for each virtual IP over the past six hours." 
- "Identify timestamps where outbound traffic exceeded 500,000 bytes, and include the virtual IP and load balancer involved." 
- "List recent health check failures with the affected virtual IPs and the load balancers that own them." 
- "Graph request rate and active connections for the virtual IP with the largest recent data transfer." 

These questions cover simple lookups, joins across the synthetic relationships, KPI rollups, and time-series slices—ideal for validating the text-to-SQL pipeline end-to-end.
