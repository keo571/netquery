# Netquery Demo Presentation
## AI-Powered Infrastructure Monitoring

**Target Audience:** Development team with limited AI knowledge
**Duration:** 20-30 minutes (depends on technical depth chosen)

---

## Slide 1: Title Slide

### Content:
```
NETQUERY
AI-Powered Infrastructure Monitoring

Turn Natural Language into Database Insights

[Your Name]
[Date]
```

### Presenter Notes:
- Keep it simple and clear
- Emphasize the transformation: natural language → insights
- Set expectation: "Today I'll show you how we can query complex infrastructure data without writing SQL"

---

## Slide 2: The Problem

### Content:
**Traditional Database Querying is Complex**

**Left Side - Example SQL Query:**
```sql
SELECT lb.name, lb.datacenter,
       COUNT(bs.id) as server_count,
       COUNT(CASE WHEN bs.health_status = 'up' THEN 1 END) as healthy_count
FROM load_balancers lb
LEFT JOIN backend_servers bs ON lb.id = bs.load_balancer_id
WHERE lb.datacenter = 'us-east-1'
GROUP BY lb.id, lb.name, lb.datacenter
HAVING COUNT(CASE WHEN bs.health_status = 'down' THEN 1 END) > 0
ORDER BY healthy_count ASC;
```

**Right Side - Pain Points:**
- ❌ Requires SQL expertise
- ❌ Need to know table relationships
- ❌ Complex joins across multiple tables
- ❌ Trial and error to get it right
- ❌ Time-consuming for simple questions

### Presenter Notes:
- "Imagine you need to check load balancer health across datacenters"
- "You'd need to know: table names, column names, how tables join together"
- "Even experienced engineers spend time debugging syntax errors"
- "What if we could just... ask?"

---

## Slide 3: The Solution

### Content:
**Just Ask in Plain English**

**Side-by-Side Comparison:**

**Left - Natural Language:**
```
"Show me load balancers in us-east-1 that have
unhealthy backend servers"
```

**Right - Result (Screenshot of your UI showing):**
- Chat interface with the question
- Table showing: Load Balancer Name | Datacenter | Server Count | Healthy Count
- Auto-generated bar chart showing server health distribution

**Key Benefit:**
✅ Query 6 infrastructure tables without SQL knowledge
✅ Get results in seconds, not minutes
✅ Automatic visualizations included

### Presenter Notes:
- "This is the same query, but in plain English"
- "The system understands what you're asking and handles all the complexity"
- "Notice the chart - it automatically detects that this data works well as a bar chart"

---

## Slide 4: How It Works - Simple Version

### Content:
**5-Step AI Pipeline**

```
┌─────────────────────────────────────┐
│  1. USER ASKS A QUESTION            │
│  "Show top 3 load balancers"        │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  2. AI FINDS RELEVANT TABLES        │
│  Uses: Semantic Search (Embeddings) │
│  Finds: load_balancers,             │
│         backend_servers, virtual_ips│
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  3. AI GENERATES SQL                │
│  Uses: Google Gemini 2.0            │
│  Creates: SELECT query with joins   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  4. SAFETY VALIDATION               │
│  Blocks: DELETE, DROP, INSERT       │
│  Allows: Only READ operations       │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  5. EXECUTE & VISUALIZE             │
│  Runs: SQL on database              │
│  Detects: Best chart type           │
│  Returns: Table + Chart + Insights  │
└─────────────────────────────────────┘
```

### Presenter Notes:
- **Step 1**: "User types a question in plain English"
- **Step 2**: "AI uses 'embeddings' - think of it like Google search but for database tables. It understands meaning, not just keywords"
- **Step 3**: "Google Gemini (similar to ChatGPT) converts the question to SQL"
- **Step 4**: "Critical safety step - blocks any dangerous operations. Read-only by design"
- **Step 5**: "Executes the query and intelligently picks visualization type"

---

## Slide 5: System Architecture

### Content:
**Technology Stack**

**Frontend (React)**
- Modern chat interface
- Real-time visualizations (Bar, Line, Pie, Scatter charts)
- CSV export for data analysis
- Session-based conversations

**Backend (Python + FastAPI)**
- LangGraph orchestration framework
- Google Gemini 2.0 Flash (LLM for SQL generation)
- Gemini Embeddings (semantic table search)
- Safety validator + SQL executor

**Database**
- Development: SQLite (9 tables, ~50 resources)
- Production: PostgreSQL (6 tables, scalable)
- Schema: Load balancers, virtual IPs, wide IPs (global DNS), backend servers, traffic stats, wide IP pools

**Production Database Schema (6 Tables):**

1. **load_balancers** - Load balancer instances (name, datacenter, status, IP)
2. **virtual_ips** - Virtual IPs for application access (VIP address, port, protocol)
3. **backend_servers** - Physical servers handling traffic (hostname, IP, health status)
4. **wide_ips** - Global DNS load balancing entries (domain, LB method, TTL)
5. **wide_ip_pools** - Pools of VIPs assigned to wide IPs (priority, ratio, enabled)
6. **traffic_stats** - Traffic metrics (requests/sec, bytes in/out, connections)

### Presenter Notes:
- "Don't worry if you're not familiar with these technologies"
- "Key point: We use Google's AI (Gemini) similar to how ChatGPT works"
- "LangGraph is a framework that chains multiple AI steps together"
- "The schema covers the full global load balancing hierarchy: DNS → VIPs → Backend Servers"

---

## Slide 6: What Makes It Special

### Content:
**Key Features**

1. **Intelligent Table Discovery**
   - Automatically finds relevant tables using semantic similarity
   - No need to specify table names
   - Handles complex multi-table queries

2. **Safety First Design**
   - Read-only operations guaranteed
   - Blocks: DELETE, DROP, INSERT, UPDATE, ALTER
   - SQL injection prevention
   - 30-second query timeout protection

3. **Automatic Visualizations**
   - Detects data patterns (time-series, aggregations, distributions)
   - Generates appropriate chart types
   - Suppresses charts when data is unsuitable (e.g., raw entity lists)

4. **Conversational Context**
   - Remembers previous questions in session
   - Handles follow-up queries naturally
   - "Show me more details" understands context

5. **Multiple Output Formats**
   - Interactive tables with pagination
   - SVG charts (no JavaScript dependencies)
   - CSV export for full datasets
   - Network topology diagrams

### Presenter Notes:
- "These features make it production-ready, not just a demo"
- "Safety is critical - we can't risk accidental data deletion"
- "The visualization intelligence saves time - no manual chart configuration"

---

## Slide 6a: Production Challenge - Schema Incompleteness

### Content:
**Real-World Production Problem**

**Challenge:**
Production databases often lack the metadata needed for text-to-SQL systems:

| Problem | Impact | Common In |
|---------|--------|-----------|
| **No Foreign Keys** | AI can't understand relationships | PostgreSQL (performance reasons) |
| **Cryptic Names** | `tbl_usr_ord` instead of `user_orders` | Legacy systems |
| **Missing Descriptions** | No documentation of table purpose | Most production DBs |
| **Mixed Data Types** | Inconsistent or unclear types | Schema evolution |

**Example Production Database:**
```sql
-- What does this mean?
CREATE TABLE lb_cfg (
  id INTEGER,
  dc VARCHAR,    -- datacenter? domain controller?
  stat VARCHAR   -- status? statistics?
);

-- No foreign key constraint!
CREATE TABLE bs_pool (
  lb_id INTEGER  -- References lb_cfg.id, but DB doesn't know
);
```

**Why This Breaks Text-to-SQL Systems:**
- ❌ AI can't find relevant tables (no descriptions)
- ❌ AI can't generate JOINs (no foreign keys)
- ❌ AI guesses wrong meanings (`dc` = "direct current"?)
- ❌ Users get errors or wrong results

### Presenter Notes:
- "This is THE biggest barrier to deploying text-to-SQL in production"
- "Many companies remove FKs for performance - but that breaks AI table discovery"
- "Even with perfect LLMs, garbage in = garbage out"
- "We needed a solution that works with real-world messy databases"

---

## Slide 6b: Solution - Schema Ingestion Pipeline

### Content:
**Universal Schema Ingestion Tool**

**What It Does:**
Builds a complete, enriched schema from **any** database - even incomplete ones.

**Two-Path Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                     PATH 1: DEV/COMPLETE DBs                │
│                                                             │
│  SQLite/MySQL with FKs                                      │
│          ↓                                                  │
│  python -m src.schema_ingestion build                       │
│          ↓                                                  │
│  Automatic Extraction:                                      │
│  • Tables & columns (via introspection)                     │
│  • Foreign keys (from DB constraints)                       │
│  • Data types (from schema)                                 │
│          ↓                                                  │
│  Canonical Schema JSON                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              PATH 2: PROD/INCOMPLETE DBs ⭐                  │
│                                                             │
│  PostgreSQL without FKs + Cryptic names                     │
│          ↓                                                  │
│  Excel Schema File (2 tabs):                                │
│  Tab 1 'table_schema': Human descriptions + types           │
│  Tab 2 'mapping': Explicit foreign key relationships        │
│          ↓                                                  │
│  python -m src.schema_ingestion build --excel prod.xlsx     │
│          ↓                                                  │
│  Canonical Schema JSON                                      │
└─────────────────────────────────────────────────────────────┘
```

**Excel Format (Path 2):**

Tab 1: `table_schema`
| table_name | column_name | data_type | table_description | column_description |
|-----------|-------------|-----------|-------------------|-------------------|
| lb_cfg | id | INTEGER | Load balancer configuration | Unique identifier |
| lb_cfg | dc | VARCHAR | Load balancer configuration | Datacenter location code |
| bs_pool | lb_id | INTEGER | Backend server pool | Load balancer reference |

Tab 2: `mapping`
| table_a | column_a | table_b | column_b |
|---------|----------|---------|----------|
| bs_pool | lb_id | lb_cfg | id |

**Output: Canonical Schema (Same Format for Both Paths)**
```json
{
  "tables": {
    "lb_cfg": {
      "name": "lb_cfg",
      "description": "Load balancer configuration",
      "columns": {
        "dc": {
          "data_type": "VARCHAR",
          "description": "Datacenter location code"
        }
      },
      "relationships": [
        {"from": "bs_pool.lb_id", "to": "lb_cfg.id"}
      ]
    }
  }
}
```

**Key Benefits:**
- ✅ Works with ANY database (complete or incomplete)
- ✅ No LLM needed for schema building (Excel provides everything)
- ✅ Version-controlled schemas (JSON + Excel in git)
- ✅ Namespace isolation (dev vs prod)
- ✅ One-time setup, then query forever

### Presenter Notes:
- "This is what makes Netquery universal - not just a toy for dev databases"
- "Path 1 is automatic - just point at your database"
- "Path 2 requires a one-time Excel file, but then works forever"
- "The Excel file is your 'source of truth' - version control it"
- "Both paths output the same canonical format - query pipeline doesn't care which you used"
- "This solves the 'last mile' problem - going from POC to production"

---

## Slide 6c: Schema Ingestion in Action

### Content:
**Real Example: Netquery Development**

**Development Environment (Path 1):**
```bash
# SQLite with foreign keys - fully automatic
python -m src.schema_ingestion build \
  --output schema_files/dev_schema.json

✓ Extracted 9 tables
✓ Found 12 foreign key relationships
✓ Generated semantic embeddings
✓ Schema ready: schema_files/dev_schema.json
```

**Production Environment (Path 2):**
```bash
# PostgreSQL without FKs - use Excel definitions
python -m src.schema_ingestion build \
  --excel schema_files/prod_schema.xlsx \
  --output schema_files/prod_schema.json \
  --schema-id prod

✓ Parsed Excel: 6 tables, 8 relationships
✓ Validated 45 columns with descriptions
✓ Generated semantic embeddings (namespace: prod)
✓ Schema ready: schema_files/prod_schema.json
```

**Now Query Either Environment:**
```python
# Development queries
python gemini_cli.py "show load balancers" --schema schema_files/dev_schema.json

# Production queries (same code!)
python gemini_cli.py "show load balancers" --schema schema_files/prod_schema.json
```

**Schema Evolution:**
```bash
# After DB changes, rebuild schema
python -m src.schema_ingestion build --output schema_files/dev_schema_new.json

# Compare what changed
python -m src.schema_ingestion diff \
  schema_files/dev_schema.json \
  schema_files/dev_schema_new.json

Output:
+ Added table: 'ssl_certificates'
~ Modified: 'load_balancers.status' (VARCHAR → ENUM)
- Removed relationship: virtual_ips → backend_servers
```

**Commands Reference:**
```bash
# Build from database (auto-detects tables, FKs, types)
python -m src.schema_ingestion build --output schema.json

# Build from Excel (for incomplete production DBs)
python -m src.schema_ingestion build --excel schema.xlsx --output schema.json

# Validate schema correctness
python -m src.schema_ingestion validate schema.json

# View schema summary
python -m src.schema_ingestion summary schema.json -v

# Compare schemas
python -m src.schema_ingestion diff old.json new.json
```

### Presenter Notes:
- "We use this tool ourselves - dev uses Path 1, prod uses Path 2"
- "The diff command is crucial for safe schema migrations"
- "Validate catches errors before you deploy"
- "Summary gives you a quick overview without reading JSON"
- "Same query code works on both environments - schema abstraction layer"

---

## Slide 7: What It Can Do - Example Queries

### Content:
**Query Capabilities**

| Category | Example Question | What It Does |
|----------|------------------|--------------|
| **Simple Lookup** | "Show all load balancers" | Displays table data |
| **Filtering** | "Which backend servers in us-east-1 have unhealthy status?" | Filters by location and status |
| **Aggregation** | "Count load balancers per datacenter" | GROUP BY with aggregation |
| **Multi-Table** | "Show each virtual IP with its associated load balancer" | Joins across tables |
| **Time Series** | "Show traffic stats from the past 24 hours" | Time-based queries with line charts |
| **Ranking** | "Show the ten most recently added load balancers" | ORDER BY with LIMIT |
| **Wide IP / Global LB** | "Show all wide IPs and their load balancing algorithms" | DNS global load balancing queries |
| **Traffic Analysis** | "Which virtual IPs have the highest traffic?" | Traffic metrics with ranking |
| **Complex** | "Show the complete path from wide IP to backend servers" | 4+ table joins with full hierarchy |

### Presenter Notes:
- "Start with simple examples, show progression to complex queries"
- "The same system handles all these query types"
- "No need to learn different syntax for different query types"

---

## Slide 8: Live Demo Setup

### Content:
**What We'll Demo Today**

**Query 1: Simple Lookup** ⭐ (Warm-up)
```
"Show all load balancers"
```
Expected: Table with load balancers showing name, datacenter, status, IP address

**Query 2: Relationship Query** ⭐⭐ (Intermediate)
```
"Show each virtual IP with its associated load balancer"
```
Expected: Table with joins showing VIP address, port, protocol, and LB name

**Query 3: Aggregation + Chart** ⭐⭐⭐ (Advanced)
```
"Count load balancers per datacenter"
```
Expected: Table + Bar chart showing LB distribution across datacenters

**Query 4: Traffic Analysis** ⭐⭐⭐ (Impressive)
```
"Show traffic stats from the past 24 hours"
```
Expected: Table + Line chart with time-series traffic data (requests/sec, bytes)

**Query 5: Complex Multi-Table** ⭐⭐⭐⭐ (Advanced)
```
"Show the complete path from wide IP to backend servers"
```
Expected: Complex join across 5 tables showing global DNS hierarchy

**Bonus: Follow-Up Question**
```
"Which of those backend servers are unhealthy?"
```
Expected: System understands context and filters for health_status = 'down'

### Presenter Notes:
- "We'll start simple and build complexity"
- "Watch how the system handles each query type"
- "Pay attention to how quickly it responds"
- "Notice the automatic chart generation"

---

## Slide 9: Real-World Query Examples

### Content:
**Production-Ready Query Categories**

**Basic Inventory:**
- "Show all load balancers"
- "List all virtual IPs"
- "Display all backend servers"

**Health & Status Monitoring:**
- "Which backend servers are unhealthy?"
- "Show load balancers with status 'active'"
- "List all backend servers and their health states"

**Relationship & Configuration:**
- "For each load balancer, list its backend servers with their status"
- "Show each virtual IP with its associated load balancer"
- "List all wide IPs with their virtual IP pool members"

**Traffic & Performance:**
- "Which virtual IPs have the highest traffic?"
- "Calculate average requests per second by datacenter"
- "Show traffic statistics with bytes transferred above 100000"

**Global Load Balancing (Wide IP):**
- "Show all wide IPs and their load balancing algorithms"
- "Which wide IPs use round-robin algorithm?"
- "Display wide IP pools with their priority and weight settings"

**Advanced Analytics:**
- "Show the complete path from wide IP to backend servers"
- "Display comprehensive load balancer overview: backends, VIPs, traffic, and status"
- "Show datacenters with more than 5 load balancers"

**Time-Based Queries:**
- "Show traffic stats from the past 24 hours"
- "List load balancers created in the last 30 days"
- "Display traffic trends over time for virtual IP id 1"

### Presenter Notes:
- "These are real queries from our test suite - they all work!"
- "Notice the variety: from simple lookups to complex multi-table analytics"
- "The system handles operational, monitoring, and planning use cases"
- "Wide IP queries show global DNS load balancing capabilities"

---

## Slide 10: Technical Deep Dive - 5-Stage Pipeline

### Content:
**LangGraph Orchestration Architecture**

```
┌──────────────────────────────────────────────────────────────────┐
│                    User Natural Language Query                    │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 1: SCHEMA ANALYZER (SMART TABLE EXPANSION)               │
│  Purpose: Find relevant tables + expand via relationships        │
│  Technology: Gemini Embeddings + FK traversal                    │
│  ────────────────────────────────────────────────────────────    │
│  Process:                                                         │
│  1. SEMANTIC SEARCH: Convert query to 768-dim embedding          │
│  2. Compare with cached table embeddings (cosine similarity)     │
│  3. Select top 5 most relevant tables (threshold: 0.15)          │
│  4. SMART FK EXPANSION:                                          │
│     • Sort by relevance score (expand best matches first)        │
│     • Phase 1: Add OUTBOUND FKs (JOIN targets)                   │
│     • Phase 2: Add INBOUND FKs (referencing tables)              │
│     • Hard cap at 15 total tables (prevent token explosion)      │
│  5. SELECTIVE SAMPLE DATA:                                       │
│     • Semantic tables (5): Full schema + 3 sample rows           │
│     • Expanded tables (10): Schema only (saves ~3k tokens)       │
│  ────────────────────────────────────────────────────────────    │
│  Output: 5-15 tables + schema + optimized samples (~7-8k tokens)│
│  Speed Optimization: 40-75% token reduction vs unbounded         │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 2: SQL GENERATOR (LLM Call #1)                           │
│  Purpose: Generate SQL directly from natural language            │
│  Technology: Gemini 2.0 Flash (temp=0.1, max_tokens=4096)       │
│  ────────────────────────────────────────────────────────────    │
│  Process:                                                         │
│  1. Build context: schema + relationships + sample data          │
│  2. Add database-specific hints (SQLite vs PostgreSQL)           │
│  3. Direct LLM call (no intermediate planning)                   │
│  4. Retry up to 3 times if SQL is invalid                        │
│  ────────────────────────────────────────────────────────────    │
│  Output: SQL query string                                        │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 3: VALIDATOR                                              │
│  Purpose: Safety-first SQL validation                            │
│  Technology: Regex + AST parsing                                 │
│  ────────────────────────────────────────────────────────────    │
│  Checks:                                                          │
│  ✓ Block destructive ops: DELETE, DROP, INSERT, UPDATE, ALTER   │
│  ✓ Prevent SQL injection patterns                                │
│  ✓ Block system table access (sqlite_master, pg_catalog)         │
│  ✓ Verify read-only SELECT queries                               │
│  ────────────────────────────────────────────────────────────    │
│  Output: Validated SQL or rejection error                        │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 4: EXECUTOR                                               │
│  Purpose: Execute SQL and retrieve results                       │
│  Technology: SQLAlchemy + Connection Pooling                     │
│  ────────────────────────────────────────────────────────────    │
│  Process:                                                         │
│  1. Execute SQL with 30-second timeout protection                │
│  2. Fetch results with smart row limiting                        │
│  3. Parse results into structured format                         │
│  4. Count total rows (fast check for >1000 rows)                 │
│  ────────────────────────────────────────────────────────────    │
│  Output: Result set + metadata (row count, execution time)       │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  Stage 5: INTERPRETER (LLM Call #2 - COMBINED)                  │
│  Purpose: Generate insights & auto-visualization in ONE call     │
│  Technology: Gemini 2.0 Flash (OPTIMIZED: 1 call, not 2)        │
│  ────────────────────────────────────────────────────────────    │
│  Process:                                                         │
│  1. Analyze result structure (columns, types, data patterns)     │
│  2. SINGLE LLM call returns JSON with:                           │
│     • summary: Brief 1-2 sentence overview                       │
│     • key_findings: 3-5 bullet points of insights                │
│     • visualization: Chart type + config (or "none")             │
│  3. Visualization options:                                       │
│     • Time-series → Line chart                                   │
│     • Aggregations → Bar chart                                   │
│     • Distributions → Pie chart                                  │
│     • Correlations → Scatter plot                                │
│     • Raw lookups → "none" (no chart)                            │
│  ────────────────────────────────────────────────────────────    │
│  Output: Combined response (analysis + visualization)            │
│  Performance: 33% faster than separate calls                     │
└──────────────────────────────────────────────────────────────────┘
                                ↓
              Final Response to User (Table + Chart + Text)
```

### Presenter Notes:
- "This is LangGraph - a framework for chaining AI operations"
- "Each stage has a specific job, making the system modular and testable"
- "If any stage fails, the error handler provides user-friendly feedback"
- "Stage 1 uses AI to find tables, Stage 2 uses AI to write SQL - both leverage LLMs"
- "Stage 3-4 are deterministic (no AI), ensuring safety and reliability"
- "Stage 5 uses pattern detection first, LLM only for complex insights"

---

## Slide 11: Technical Deep Dive - Embedding Search Explained

### Content:
**How Semantic Table Discovery Works**

**Example: "Show load balancers with their backend servers"**

**Step 1: Embedding Generation (One-Time Setup)**
```
Table Descriptions → Gemini Embeddings API → 768-dimensional vectors

load_balancers: "Load balancer instances managing traffic distribution"
→ [0.23, -0.45, 0.87, 0.12, -0.33, ..., 0.56]  (768 numbers)

backend_servers: "Physical servers handling actual traffic"
→ [0.19, -0.42, 0.91, 0.08, -0.29, ..., 0.61]  (768 numbers)

virtual_ips: "Virtual IP addresses for application access"
→ [-0.12, 0.33, -0.45, 0.78, 0.22, ..., -0.18]  (768 numbers)
```
*Cached in `.embeddings_cache/` directory - no re-computation needed*

**Step 2: Query Embedding (Runtime)**
```
User query: "Show load balancers with their backend servers"
→ Gemini Embeddings API
→ [0.21, -0.43, 0.88, 0.10, -0.31, ..., 0.58]  (768 numbers)
```

**Step 3: Cosine Similarity Calculation**
```
Similarity = dot(query_vector, table_vector) / (||query|| × ||table||)

Scores:
- load_balancers:  0.92 ✓ (high similarity - selected)
- backend_servers: 0.88 ✓ (high similarity - selected)
- virtual_ips:     0.65 ✓ (moderate similarity - selected)
- traffic_stats:   0.23 ✗ (low similarity - ignored)
- wide_ips:        0.15 ✗ (below threshold - ignored)

Threshold: 0.15 (configurable)
Top 5 tables sent to SQL generator
```

**Step 4: Context Building**
```
Selected tables → Full schema details

For load_balancers:
  Columns: id (INTEGER), name (VARCHAR), datacenter (VARCHAR), status (VARCHAR)
  Relationships: one-to-many with backend_servers via id
  Sample data: [{'id': 1, 'name': 'lb-us-east-1a', ...}]

For backend_servers:
  Columns: id, hostname, ip_address, health_status, load_balancer_id
  Relationships: many-to-one with load_balancers via load_balancer_id
  Sample data: [{'id': 1, 'hostname': 'web-server-01', ...}]
```

**Why Embeddings Are Powerful:**
- ✅ Understands synonyms: "servers" = "machines" = "hosts"
- ✅ Captures concepts: "unhealthy" matches "health_status" column
- ✅ Language-agnostic: Works with abbreviations, technical jargon
- ✅ Context-aware: "traffic" relates to both network_traffic and requests
- ✅ Fast: Pre-cached embeddings = millisecond lookup

### Presenter Notes:
- "Embeddings are like coordinates in high-dimensional space"
- "Similar concepts are closer together in this space"
- "Think of it like Google search - understands intent, not just keywords"
- "We pre-compute table embeddings once, then just embed the query at runtime"
- "768 dimensions sounds complex, but it's just how the AI represents meaning"
- "The cosine similarity is a measure of how 'parallel' two vectors are"

---

## Slide 11a: Technical Deep Dive - Smart FK Expansion (Speed Optimization)

### Content:
**How We Prevent Token Explosion While Maintaining Accuracy**

**The Problem: Unbounded FK Expansion**

Without limits, a simple query could explode:
```
User asks: "Show customers who ordered recently"

Semantic Search finds: customers (0.95), orders (0.92)
  ↓
Naive FK Expansion (NO LIMITS):
  customers → addresses, payments, customer_notes, loyalty_points, ...
  orders → order_items, shipments, returns, refunds, invoices, ...
  order_items → products, discounts, ...
  products → categories, suppliers, reviews, ...

Result: 5 semantic tables → 30+ expanded tables
        30 tables × 1000 tokens = 30,000 tokens just for schema!
        LLM processing: 3-5 seconds just to READ schema
        API cost: 3x higher
```

**Our Solution: 4-Layer Speed Optimization**

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: HARD LIMITS (Prevent Explosion)                      │
├─────────────────────────────────────────────────────────────────┤
│  • max_relevant_tables: 5  (semantic search results)            │
│  • max_expanded_tables: 15 (total after FK expansion)           │
│  • max_schema_tokens: 8000 (safety net, ~25% of context)        │
│                                                                  │
│  Impact: 5 → max 15 tables (not 30+)                            │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: SMART PRIORITIZATION (Best Tables First)             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Sort by semantic score                                │
│    customers (0.95) → expand first                              │
│    orders (0.92)    → expand second                             │
│                                                                  │
│  Phase 2: Prioritize OUTBOUND FKs (needed for JOINs)            │
│    customers.address_id     → addresses ✓ HIGH PRIORITY         │
│    orders.customer_id       → customers ✓ HIGH PRIORITY         │
│    orders.shipping_id       → addresses ✓ HIGH PRIORITY         │
│                                                                  │
│  Phase 3: Add INBOUND FKs if budget remains                     │
│    payments.customer_id     → customers (if space)              │
│    order_items.order_id     → orders (if space)                 │
│                                                                  │
│  Impact: Most relevant tables included, least relevant dropped  │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: SELECTIVE SAMPLE DATA (Huge Token Saver)             │
├─────────────────────────────────────────────────────────────────┤
│  Semantic matches (5 tables):                                   │
│    ✓ Full schema + column descriptions                          │
│    ✓ 3 sample rows per table (~700 tokens/table)                │
│    Why: LLM needs examples to understand data patterns          │
│                                                                  │
│  FK-expanded tables (10 tables):                                │
│    ✓ Full schema + column descriptions                          │
│    ✗ NO sample rows (~400 tokens/table)                         │
│    Why: LLM only needs to know they're joinable                 │
│                                                                  │
│  Token savings: 10 tables × 300 tokens = 3,000 tokens saved!    │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: TOKEN BUDGET TRACKING (Safety Net)                   │
├─────────────────────────────────────────────────────────────────┤
│  Real-time tracking:                                             │
│    for table in expanded_tables:                                │
│      if current_tokens >= 8000:  # Budget limit                 │
│        stop adding tables                                        │
│      current_tokens += estimate_tokens(table)                   │
│                                                                  │
│  Logging: "Schema context: 12 tables, ~6,800 tokens"            │
│  Warning: "Token budget reached. Skipping 3 tables."            │
└─────────────────────────────────────────────────────────────────┘
```

**Example: E-commerce Query**

```
Query: "Show customers who ordered in the last month"

BEFORE OPTIMIZATION:
─────────────────────
Semantic: customers (0.95), orders (0.92)
FK Expansion: UNLIMITED
  → 18 tables (customers, orders, addresses, payments,
     order_items, products, shipments, returns, ...)
  → All tables get sample data
  → 18 tables × 1000 tokens = 18,000 tokens
  → LLM processing: ~1.8s just for schema
  → Response time: 6-8 seconds total

AFTER OPTIMIZATION:
──────────────────
Semantic: customers (0.95), orders (0.92)  [5 tables]
Smart Expansion:
  Phase 1 (Outbound): addresses, order_items  [+ 2 tables]
  Phase 2 (Inbound): payments, shipments     [+ 2 tables]
  Stopped at 12 tables (limit: 15)

Sample data: ONLY customers + orders (semantic matches)
Expanded tables: Schema only (no samples)

  → 12 tables, ~7,200 tokens
  → LLM processing: ~0.72s (2.5x faster!)
  → Response time: 4-5 seconds total (33% faster)
  → API cost: 60% lower
```

**Performance Metrics**

| Database Size | Before | After | Improvement |
|---------------|--------|-------|-------------|
| Small (10 tables) | 5→8 tables<br/>~6k tokens | 5→8 tables<br/>~4.5k tokens | 25% faster |
| Medium (50 tables) | 5→18 tables<br/>~13k tokens | 5→15 tables<br/>~7.5k tokens | 42% faster |
| Large (200 tables) | 5→40+ tables<br/>~30k+ tokens | 5→15 tables<br/>~7.5k tokens | **75% faster** |

**Configuration (Tunable)**

```python
# In config.py or environment variables
max_relevant_tables = 5      # Semantic search limit
max_expanded_tables = 15     # FK expansion cap (3x semantic)
max_schema_tokens = 8000     # Token budget (~25% of 32k context)
```

**Key Benefits:**
- ⚡ **3-4x faster** LLM response (less context to process)
- 💰 **40-75% lower** API costs (fewer tokens)
- 🎯 **Same accuracy** (smart prioritization keeps relevant tables)
- 🛡️ **Protected** (token budget prevents worst-case scenarios)

### Presenter Notes:
- "This optimization was critical for production readiness"
- "Without limits, large databases could blow up to 30-40 tables"
- "Smart prioritization ensures we keep the BEST tables, not just any tables"
- "Selective sample data is a huge win - expanded tables don't need examples"
- "This is why our response times are 4-5 seconds, not 10+ seconds"
- "The token budget is a safety net - catches edge cases automatically"

---

## Slide 12: Technical Deep Dive - SQL Generation Prompt

### Content:
**What We Send to the LLM**

**Input to Gemini 2.0 Flash:**

```
System Role:
You are an expert SQL query generator. Generate precise, efficient SQL
queries based on natural language requests and database schema information.

Database Type: PostgreSQL
Read-Only: Only SELECT queries allowed

Schema Context (from embedding search):
──────────────────────────────────────────────────────────────────
TABLE: load_balancers
Description: Load balancer instances managing traffic distribution
Columns:
  • id (INTEGER, PRIMARY KEY) - Unique load balancer identifier
  • name (VARCHAR) - Load balancer name
  • datacenter (VARCHAR) - Datacenter location where LB is deployed
  • status (VARCHAR) - Current operational status (active/inactive/maintenance)
  • ip_address (VARCHAR) - Management IP address
  • created_at (TIMESTAMP) - When the load balancer was created
Relationships:
  → ONE-TO-MANY with backend_servers (via id → load_balancer_id)
  → ONE-TO-MANY with virtual_ips (via id → load_balancer_id)
Sample rows (first 3):
  {'id': 1, 'name': 'lb-us-east-1a', 'datacenter': 'us-east-1', 'status': 'active'}
  {'id': 2, 'name': 'lb-us-west-2b', 'datacenter': 'us-west-2', 'status': 'active'}
  ...

TABLE: backend_servers
Description: Physical servers handling actual traffic
Columns:
  • id (INTEGER, PRIMARY KEY) - Unique backend server identifier
  • hostname (VARCHAR) - Server hostname
  • ip_address (VARCHAR) - Server IP address
  • health_status (VARCHAR) - Current health check status (up/down/unknown)
  • load_balancer_id (INTEGER, FOREIGN KEY) - Load balancer managing this server
  • datacenter (VARCHAR) - Datacenter location
Sample rows:
  {'id': 1, 'hostname': 'web-01', 'health_status': 'up', 'load_balancer_id': 1}
  ...
──────────────────────────────────────────────────────────────────

User Question:
"Show load balancers with their backend servers"

Requirements:
1. Generate syntactically correct PostgreSQL SQL
2. Use appropriate JOINs based on relationships
3. Include relevant columns from both tables
4. Return results sorted logically
5. Use table aliases for readability
6. Return ONLY the SQL query, no explanations

Generate SQL:
```

**Output from LLM:**
```sql
SELECT
    lb.id AS load_balancer_id,
    lb.name AS load_balancer_name,
    lb.datacenter,
    lb.status AS lb_status,
    bs.id AS server_id,
    bs.hostname,
    bs.ip_address AS server_ip,
    bs.health_status
FROM load_balancers lb
LEFT JOIN backend_servers bs ON lb.id = bs.load_balancer_id
ORDER BY lb.name, bs.hostname;
```

**Key Prompt Engineering Techniques:**
- ✅ Role definition: "You are an expert SQL query generator"
- ✅ Constraints: Database type, read-only enforcement
- ✅ Rich context: Full schema + relationships + sample data
- ✅ Clear requirements: What makes a good SQL query
- ✅ Output format: "Return ONLY the SQL query"
- ✅ Low temperature (0.1): Deterministic, consistent output

### Presenter Notes:
- "We're not just sending the question - we're giving the LLM everything it needs"
- "Sample data helps the LLM understand actual values and data types"
- "Relationships are critical - the LLM knows how to join tables"
- "Temperature 0.1 means minimal randomness - same query → same SQL"
- "This is 'prompt engineering' - crafting the input to get reliable output"
- "The LLM has seen millions of SQL examples during training"

---

## Slide 13: Technical Deep Dive - Production Architecture

### Content:
**Complete System Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                          │
│                    (React 19 - Port 3000)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ UI Components:                                           │  │
│  │  • Chat interface with SSE streaming responses           │  │
│  │  • Progressive data loading (10→30→100 rows)             │  │
│  │  • Smart chart suppression (Recharts library)            │  │
│  │  • Schema overview on startup                            │  │
│  │  • CSV export with server-side streaming                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ State Management (React Hooks):                          │  │
│  │  • useChat: Message history, loading states              │  │
│  │  • useScrollBehavior: Auto-scroll to new messages        │  │
│  │  • useState/useCallback: Component state                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓ Server-Sent Events (SSE)
┌─────────────────────────────────────────────────────────────────┐
│                      ADAPTER LAYER                              │
│                 (FastAPI + httpx - Port 8001)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ In-Memory Session Store (1-hour TTL):                    │  │
│  │  • Last 5 conversation exchanges per session             │  │
│  │  • Stores: user_message, SQL, timestamp                  │  │
│  │  • Auto-cleanup of expired sessions                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Context-Aware Prompt Engineering:                        │  │
│  │  • Injects last 3 exchanges into prompt                  │  │
│  │  • Domain-agnostic conversation rules                    │  │
│  │  • Handles follow-ups: "show their names", "also add X"  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ SSE Event Stream (6 event types):                        │  │
│  │  1. session → Session ID                                 │  │
│  │  2. sql → Generated SQL query                            │  │
│  │  3. data → Query results (1-2s)                          │  │
│  │  4. analysis → LLM interpretation (3-5s)                 │  │
│  │  5. visualization → Chart config (5-8s)                  │  │
│  │  6. done → Stream complete                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓ Internal HTTP API
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND API LAYER                          │
│                 (FastAPI - Port 8000)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ API Endpoints:                                          │   │
│  │  • POST /api/generate-sql   → Generate SQL only        │   │
│  │  • GET  /api/execute/{id}   → Execute + preview        │   │
│  │  • POST /api/interpret/{id} → LLM insights + viz       │   │
│  │  • GET  /api/download/{id}  → Stream full CSV          │   │
│  │  • GET  /health             → System health            │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ In-Memory Cache (10-minute TTL):                       │   │
│  │  • Stores up to 100 rows per query                     │   │
│  │  • Avoids re-execution for interpretation              │   │
│  │  • Future: Redis for production scaling               │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH PIPELINE LAYER                     │
│                   (5-Stage Processing)                          │
│  Schema Analyzer → SQL Generator → Validator → Executor →      │
│  Interpreter                                                    │
└───────────┬──────────────────────────────────┬──────────────────┘
            ↓                                   ↓
┌───────────────────────────┐    ┌────────────────────────────────┐
│  GOOGLE GEMINI API        │    │  DATABASE LAYER                │
│  • Embeddings API         │    │  Dev:  SQLite (9 tables)       │
│  • Gemini 2.0 Flash       │    │  Prod: PostgreSQL (6 tables)   │
│  • Temperature: 0.1       │    │  • Connection pooling          │
│  • Max tokens: 4096       │    │  • 30s query timeout           │
│  • Retry logic: 3x        │    │  • Read-only enforcement       │
└───────────────────────────┘    └────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE & CACHE LAYER                        │
│  ┌────────────────────────┐    ┌───────────────────────────┐   │
│  │ Embedding Cache        │    │ Schema Files              │   │
│  │ .embeddings_cache/     │    │ schema_files/             │   │
│  │ • Local file storage   │    │ • dev_schema.json         │   │
│  │ • Namespace isolation  │    │ • prod_schema.json        │   │
│  │ • 768-dim vectors      │    │ • Canonical format        │   │
│  └────────────────────────┘    └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Data Flow Example (SSE Streaming):**

```
1. User types: "Show load balancers in us-east-1"
   ↓
2. Frontend → POST /chat to Adapter (port 8001) with session_id
   ↓
3. Adapter:
   • Retrieves last 3 conversations from in-memory session store
   • Builds context prompt: "CONVERSATION HISTORY: [last 3 exchanges]"
   • Injects domain-agnostic rules for follow-up questions
   ↓
4. Adapter → Streams to Backend (port 8000):
   ↓
   Event 1 (immediate): session_id
   Frontend: Displays typing indicator
   ↓
   Event 2 (0.5s): SQL query generated (LLM Call #1)
   Frontend: Shows SQL syntax-highlighted
   ↓
   Event 3 (1-2s): Query results (100 rows cached, 30 shown)
   Frontend: Renders table with pagination ✓ USER SEES DATA NOW
   ↓
   Event 4 (3-4s): COMBINED interpretation event (LLM Call #2)
   Frontend: Shows analysis + key findings + chart together
   OPTIMIZATION: Previously 2 events (analysis + viz), now combined!
   ↓
   Event 5 (done): Stream complete
   Frontend: Removes all loading spinners

Total perceived time: 1-2s (data visible)
Total actual time: 4-5s (full response with chart)
Improvement vs old 3-call approach: 40% faster (was 6-8s, now 4-5s)
Improvement vs synchronous: 3-5x faster perceived performance
```

**Technology Stack Summary:**

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19 + Recharts | User interface & visualization |
| Adapter | FastAPI | Session management |
| Backend API | FastAPI + Uvicorn | RESTful endpoints |
| Pipeline | LangGraph | AI workflow orchestration |
| LLM | Google Gemini 2.0 Flash | SQL generation (1 call) + Combined analysis/viz (1 call) = 2 total |
| Embeddings | Gemini Embeddings | Semantic table search |
| Database | SQLite / PostgreSQL | Data storage |
| ORM | SQLAlchemy | Database abstraction |
| Caching | In-memory dict | Query result caching |

**LLM Call Optimization:**
- Stage 2 (SQL Generation): 1 LLM call
- Stage 5 (Interpretation): 1 LLM call (COMBINED analysis + visualization)
- **Total per query**: 2 LLM calls (down from 3)
- **Cost savings**: 33% reduction in API costs
- **Speed improvement**: 33% faster responses (4-5s vs 6-8s)

### Presenter Notes:
- "This is a production-ready architecture with clear separation of concerns"
- "Three-tier design: Frontend, API, Pipeline"
- "The adapter layer is the secret sauce - handles sessions and context"
- "SSE streaming gives 3-5x faster perceived performance"
- "Users see data in 1-2 seconds, not 4-5 seconds total"
- "Progressive disclosure: each part appears as soon as it's ready"
- "LangGraph provides observability - we can see which stage fails"
- "Recent optimization: Combined analysis + visualization into 1 LLM call (33% cost/speed improvement)"
- "We went from 3 LLM calls per query down to 2 - significant savings at scale"

---

## Slide 13a: Technical Deep Dive - Frontend Architecture Decisions

### Content:
**Key Frontend Design Patterns**

**1. Server-Sent Events (SSE) for Progressive Loading**

**Problem:** Users waited 5-8 seconds before seeing ANY results

**Solution:** Stream response parts as they become available
```javascript
// Backend streams 6 event types:
Event 1: session_id (immediate)
Event 2: sql (0.5s) → User sees SQL immediately
Event 3: data (1-2s) → User sees TABLE immediately ⭐
Event 4: analysis (3-5s) → User reads interpretation
Event 5: visualization (5-8s) → User sees chart
Event 6: done
```

**Why SSE over WebSockets?**
- ✅ Simpler: One-way data flow (server → client)
- ✅ Native HTTP: Works through proxies, load balancers
- ✅ No reconnection complexity needed
- ✅ Less overhead: No handshake, no ping/pong

**Result:** 3-5x faster perceived performance

---

**2. Context-Aware Conversation (Adapter Layer)**

**Problem:** Follow-up questions like "show their names" fail without context

**Solution:** In-memory session store with smart prompt injection

```python
# Session Store (1-hour TTL):
sessions[session_id] = {
    'history': [
        {'user_message': 'Show load balancers', 'sql': 'SELECT...'},
        {'user_message': 'In us-east-1', 'sql': 'SELECT...WHERE dc=...'},
        {'user_message': 'Show their backend servers', 'sql': 'SELECT...JOIN...'}
    ]
}

# Prompt Engineering (Last 3 exchanges):
context = """
CONVERSATION HISTORY - Use this to understand follow-up questions:

Exchange 1:
  User asked: Show load balancers
  SQL query: SELECT * FROM load_balancers;

Exchange 2:
  User asked: In us-east-1
  SQL query: SELECT * FROM load_balancers WHERE datacenter='us-east-1';

Exchange 3:
  User asked: Show their backend servers
  SQL query: SELECT lb.name, bs.hostname FROM load_balancers lb
             JOIN backend_servers bs ON lb.id=bs.load_balancer_id
             WHERE lb.datacenter='us-east-1';

USER'S NEW QUESTION: Which ones are unhealthy?
"""
```

**Domain-Agnostic Rules:**
1. **Resolve references** - "their", "the pool", "those" → entities from prior queries
2. **Preserve intent** - "also show X" → modify previous SELECT
3. **Maintain consistency** - Keep filters/joins unless explicitly changed

**Why In-Memory (not Redis)?**
- ✅ Fast: Sub-millisecond lookup
- ✅ Simple: No external dependencies
- ✅ Good enough: 1-hour TTL handles typical sessions
- ⚠️ Limitation: Sessions lost on restart (acceptable for POC)

---

**3. Progressive Data Disclosure**

**Problem:** Large datasets slow to render, unnecessary data transfer

**Solution:** Multi-tier loading strategy

```javascript
Backend: Fetches max 100 rows (cached)
   ↓
Initial Display: Shows 10 rows immediately
   ↓
User Clicks "Load More": Shows next 10 rows (up to 30 total)
   ↓
User Clicks "Download CSV": Server streams full dataset (no limit)
```

**Configuration:**
```javascript
pageSize = 10        // Rows per "Load more" click
maxDisplay = 30      // Max in browser (UX limit)
BACKEND_LIMIT = 100  // Netquery cache limit
```

**Why 100 row limit?**
- ✅ Optimal for LLM analysis (token efficiency)
- ✅ Fast preview for most queries
- ✅ Reasonable memory footprint
- ✅ Transparent via "data_truncated" flag

---

**4. Smart Chart Suppression**

**Problem:** LLM suggests charts for unsuitable data (entity lists, relationships)

**Solution:** Client-side validation before rendering

```javascript
// Suppress if:
const shouldSuppressChart = (data) => {
  // 1. No numeric aggregates (count, sum, avg)
  const hasAggregates = Object.keys(data[0]).some(key =>
    key.match(/count|sum|avg|total|max|min/)
  );
  if (!hasAggregates) return true;

  // 2. Too many string columns (relationship data)
  const stringColumns = Object.values(data[0])
    .filter(v => typeof v === 'string').length;
  if (stringColumns > data.length * 0.6) return true;

  // 3. Non-aggregated entity lists
  if (data.length > 50 && !hasAggregates) return true;

  return false; // Show chart
};
```

**Why Client-Side?**
- ✅ Frontend has actual data shape
- ✅ LLM only sees SQL, not result structure
- ✅ Better UX: No misleading visualizations

---

**5. Recharts for Visualization**

**Why Recharts (not Chart.js or D3)?**

| Feature | Recharts | Chart.js | D3.js |
|---------|----------|----------|-------|
| React-native | ✅ Yes | ❌ jQuery wrapper | ❌ Imperative |
| Declarative | ✅ JSX components | ❌ Config objects | ❌ Manual DOM |
| Responsive | ✅ Built-in | ⚠️ Requires plugin | ⚠️ Manual |
| Bundle size | ~400KB | ~200KB | ~500KB |
| Learning curve | Low | Medium | High |

**Usage:**
```jsx
<ResponsiveContainer width="100%" height={400}>
  <BarChart data={results}>
    <XAxis dataKey="datacenter" />
    <YAxis />
    <Bar dataKey="count" fill="#8884d8" />
    <Tooltip />
  </BarChart>
</ResponsiveContainer>
```

---

**6. Schema Overview on Startup**

**Problem:** Users don't know what data is available

**Solution:** Fetch schema on app load, display in welcome message

```javascript
useEffect(() => {
  const loadOverview = async () => {
    const schema = await fetchSchemaOverview(); // GET /schema/overview
    setSchemaOverview(schema); // Display: 6 tables, descriptions
  };
  loadOverview();
}, []);
```

**Benefits:**
- ✅ Discoverability: Users see available tables
- ✅ Reduces errors: Prevents questions about non-existent tables
- ✅ Onboarding: New users get immediate guidance
- ✅ Non-blocking: Chat works even if schema fetch fails

---

**Technology Stack:**

| Component | Technology | Version | Why? |
|-----------|-----------|---------|------|
| UI Framework | React | 19.1.0 | Hooks API, excellent ecosystem |
| State Management | React Hooks | Built-in | Simple needs, no Redux overhead |
| Charts | Recharts | 3.2.1 | React-native, declarative |
| HTTP Client (Frontend) | Fetch API | Native | Built-in, SSE support |
| Backend Adapter | FastAPI | 0.117.1 | Async, SSE streaming |
| HTTP Client (Backend) | httpx | 0.28.1 | Async HTTP for Python |
| Session Storage | In-memory dict | Native | Fast, simple, POC-appropriate |

### Presenter Notes:
- "The frontend is deceptively simple - React hooks only, no Redux"
- "SSE streaming is the key to perceived performance - 3-5x faster"
- "The adapter layer handles ALL conversation context - backend stays stateless"
- "Smart chart suppression prevents misleading visualizations"
- "Progressive loading means fast feedback for users"
- "In-memory sessions are fine for POC - clear path to Redis later"
- "Every architectural decision has clear rationale and trade-offs"

---

## Slide 15: Technical Deep Dive - Testing & Quality Assurance

### Content:
**Comprehensive Evaluation Framework**

**Test Suite Overview:**

| Environment | Query Set | Test Count | Coverage |
|------------|-----------|------------|----------|
| Dev (SQLite) | `testing/query_sets/dev.json` | 80+ queries | 15 categories |
| Prod (PostgreSQL) | `testing/query_sets/prod.json` | 90+ queries | 16 categories |

**Query Categories Tested:**

**Common to Both Environments:**
- ✅ Basic Queries (table lookups, filtering)
- ✅ Health & Status Monitoring
- ✅ Aggregations & Summaries
- ✅ Multi-Table Joins (2-5 tables)
- ✅ Time-based Queries
- ✅ Comparative & Advanced (above/below average)
- ✅ HAVING & Aggregation Filters
- ✅ String Operations (LIKE, pattern matching)
- ✅ Conditional Logic (CASE statements)
- ✅ Existence & NULL Checks
- ✅ Complex Analytics
- ✅ Edge Cases (error handling, safety)

**Production-Specific:**
- ✅ Wide IP & Global Load Balancing (DNS routing)
- ✅ Traffic Analysis (requests/sec, bandwidth, connections)

**Development-Specific:**
- ✅ SSL Certificate Management (expiry tracking)
- ✅ Network Monitoring (latency, packet loss)

**Evaluation Metrics:**

```
Pipeline Stage Success Tracking:
┌─────────────────────┬──────────┬──────────────────────────────┐
│ Stage               │ Status   │ What It Measures             │
├─────────────────────┼──────────┼──────────────────────────────┤
│ Schema Analysis     │ SUCCESS  │ Table discovery accuracy     │
│ SQL Generation      │ SUCCESS  │ Valid SQL generation rate    │
│ SQL Validation      │ SUCCESS  │ Safety check pass rate       │
│ Query Execution     │ SUCCESS  │ Database execution success   │
│ Chart Generation    │ Type     │ Visualization detection      │
└─────────────────────┴──────────┴──────────────────────────────┘

Technical Success Rate = (Successful / Total) × 100%
Target: 85%+ success rate across all query types
```

**Failure Analysis:**

| Failure Type | Cause | Example |
|-------------|-------|---------|
| SCHEMA_FAIL | Table/column not found | Query references non-existent table |
| GEN_FAIL | LLM unable to generate SQL | Ambiguous query phrasing |
| VALID_FAIL | Safety validation rejected | Attempted UPDATE query |
| EXEC_FAIL | Database error | Syntax error in generated SQL |
| TIMEOUT | Query took >30 seconds | Complex join on large dataset |

**Running Evaluations:**

```bash
# Full evaluation suite (generates HTML report)
python testing/evaluate_queries.py

# Single query testing
python testing/evaluate_queries.py --single "Show load balancers"

# Output: testing/evaluations/query_evaluation_report.html
```

**Sample Output:**
```
🚀 Starting Netquery Evaluation...
   Environment: prod
   Query file:  testing/query_sets/prod.json

📊 Testing 90 queries across 16 categories

📂 Basic Queries (6/6 passed)
   ✅ "Show all load balancers" (1.2s, 50 rows)
   ✅ "List all virtual IPs" (0.8s, 75 rows)

📂 Wide IP & Global Load Balancing (8/8 passed)
   ✅ "Show all wide IPs and their load balancing algorithms" (1.5s, 12 rows) [bar]
   ✅ "Which wide IPs use round-robin algorithm?" (1.1s, 5 rows)

📂 Complex Analytics (5/6 passed)
   ✅ "Show the complete path from wide IP to backend servers" (2.3s, 45 rows)
   ❌ "Show nonexistent table data" (SCHEMA_FAIL)

================================================================================
📈 EVALUATION SUMMARY
================================================================================

📊 Key Metrics:
  Overall Success Rate: 78/90 (86.7%)
  Charts Generated:     22
  Average Query Time:   1.8 seconds

🔧 Failure Breakdown:
  Schema Failures:    3  (invalid table references)
  Generation Failures: 5  (ambiguous queries)
  Validation Failures: 2  (attempted unsafe operations)
  Execution Failures:  2  (SQL syntax edge cases)

📈 By Category:
  Basic Queries: 6/6 (100.0%)
  Wide IP & Global LB: 8/8 (100.0%)
  Complex Analytics: 5/6 (83.3%)
  Edge Cases: 0/5 (0.0%) ← Expected failures for safety testing
```

**Quality Assurance Process:**
1. **Automated Testing**: Run evaluation suite after any pipeline changes
2. **Regression Testing**: Ensure previously passing queries still pass
3. **Edge Case Coverage**: Intentional failures (DELETE, DROP) verify safety
4. **Performance Benchmarking**: Track query execution times
5. **Chart Detection**: Validate automatic visualization suggestions

### Presenter Notes:
- "We have comprehensive test coverage - 170+ total test queries"
- "The evaluation framework tests end-to-end: from natural language to results"
- "86%+ success rate is excellent for a text-to-SQL system"
- "Edge cases intentionally fail - they test our safety validation"
- "HTML reports make it easy to track progress over time"
- "Each pipeline stage is tracked separately for debugging"

---

## Slide 16: Limitations & Future Work

### Content:
**Current Limitations**

1. **Accuracy Dependent on AI Model**
   - Complex queries may need retry or rephrasing
   - Occasional SQL syntax errors (handled with retry logic)

2. **Read-Only Operations**
   - By design, cannot modify data
   - For safety, no INSERT/UPDATE/DELETE support

3. **Schema Ingestion Initial Setup**
   - Production databases require one-time Excel schema file creation
   - Excel file must be kept in sync with database changes

**Future Enhancements**

- 📊 More chart types (heatmaps, network graphs)
- 🧠 Query history and favorites
- 🔄 Multi-database support (query across environments)
- 📈 Performance optimization for large datasets
- 🤖 Fine-tuned model on our specific schema

### Presenter Notes:
- "Be honest about limitations - builds trust"
- "The retry logic handles most AI errors automatically"
- "Read-only is a feature, not a bug - prioritizing safety"
- "We're actively working on these improvements"

---

## Slide 17: Questions & Discussion

### Content:
**Common Questions**

**Q: Can it handle any database?**
A: Yes! Works with SQLite (dev) and PostgreSQL (prod). Can be adapted to MySQL, Oracle, etc.

**Q: What if it generates wrong SQL?**
A:
- System shows the SQL for transparency
- Retry logic attempts multiple generations
- You can always write SQL manually as fallback

**Q: How secure is it?**
A:
- Read-only validation prevents data modification
- SQL injection detection built-in
- Query timeout prevents resource exhaustion
- API keys managed securely via environment variables

**Q: Does it work for non-technical users?**
A: Yes! That's the goal. Analysts, operators, and managers can query data without SQL training.

**Q: What does it cost?**
A: Google Gemini API pricing: ~$0.10 per 1M input tokens. For typical queries: <$0.001 per query.

**Q: Does it work with production databases that lack foreign keys?**
A: Yes! That's exactly what the Schema Ingestion tool solves. You create a one-time Excel file defining relationships and descriptions, and the system converts it to our canonical format. No database changes needed.

**Q: What if my database has cryptic table names?**
A: The Excel schema file lets you provide human-readable descriptions for every table and column. The AI uses these descriptions (not the cryptic names) to understand your question.

### Presenter Notes:
- "Anticipate these questions and prepare answers"
- "Have cost calculator ready if finance team is present"
- "Emphasize the productivity gains vs. API costs"

---

## Slide 18: Try It Yourself

### Content:
**Getting Started**

**Development Setup:**
```bash
# Clone repos
git clone [backend-repo]
git clone [frontend-repo]

# Backend setup
cd netquery
./start-dev.sh

# Frontend setup
cd netquery-insight-chat
npm install && npm start

# Open browser
http://localhost:3000
```

**Environment Variables Needed:**
```bash
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///data/infrastructure.db
```

**Documentation:**
- README.md - Quick start guide
- STARTUP_GUIDE.md - Detailed setup instructions
- Demo video: [Link to recording]

**Contact:**
- Email: [your-email]
- Slack: [your-slack-handle]

### Presenter Notes:
- "We want to make this accessible for your projects too"
- "Setup takes about 10 minutes"
- "Happy to pair with anyone interested in trying it"

---

## END OF PRESENTATION

---

# Additional Resources for Presenter

## Pre-Demo Checklist

Before starting your presentation:

- [ ] Both servers running (backend on 8000, frontend on 3000)
- [ ] Test all 4 demo queries and verify they work
- [ ] Clear browser cache/cookies for clean demo
- [ ] Open browser console (in case you need to debug)
- [ ] Have backup queries ready in case one fails
- [ ] Check GEMINI_API_KEY is set and valid
- [ ] Database has sample data populated
- [ ] Screenshots prepared (in case live demo fails)
- [ ] Timer/clock visible (don't run over time)

## Backup Queries (If Primary Queries Fail)

**Simple Fallbacks:**
```
1. "Show all load balancers"
2. "List all virtual IPs"
3. "Display all backend servers"
4. "Count load balancers per datacenter"
5. "Which backend servers are unhealthy?"
```

**Intermediate Fallbacks:**
```
6. "Show load balancers in maintenance mode"
7. "List virtual IPs with their IP addresses and ports"
8. "Which wide IPs are currently disabled?"
9. "Show the distribution of load balancer types"
10. "For each load balancer, list its backend servers with their status"
```

## Demo Flow Tips

1. **Start with welcome screen visible** - shows schema overview
2. **Type slowly** - let audience see the question being formed
3. **Narrate what you're doing** - "I'm asking for load balancers..."
4. **Highlight key UI elements** - point to chart, export button, etc.
5. **Show generated SQL** (if visible in UI) - transparency builds trust
6. **Export CSV** - demonstrate the practical use case
7. **Ask follow-up** - show conversational capabilities

## Common Demo Pitfalls to Avoid

❌ Don't rush through queries - give AI time to respond
❌ Don't apologize for loading time - it's actually fast
❌ Don't skip over visualizations - that's a key feature
❌ Don't ignore errors - use them as teaching moments
❌ Don't assume audience knows AI terms (explain embeddings, LLM, etc.)

## If Something Goes Wrong

**Scenario 1: Query fails with error**
- "Great example of error handling! Notice the user-friendly message"
- Try rephrasing: "Let me ask that differently..."
- Use backup query

**Scenario 2: Wrong SQL generated**
- "This shows why we have retry logic - let me try again"
- Explain: "AI is probabilistic, not deterministic"

**Scenario 3: Server crashes**
- Have screenshots ready as backup
- "Let me show you the recording instead"
- Continue presentation without live demo

**Scenario 4: Slow response**
- "The AI is analyzing 9 tables to find the right data..."
- Fill time by explaining what's happening in the pipeline

## Post-Demo Actions

- [ ] Share presentation slides with team
- [ ] Send follow-up email with setup instructions
- [ ] Schedule office hours for hands-on demo
- [ ] Collect feedback via survey
- [ ] Record demo video for those who missed it

## Metrics to Mention (If Asked)

- **Query response time**: 4-5 seconds average (down from 6-8s after optimization)
- **Accuracy**: ~85-90% first-try success rate
- **Tables supported**: 9 (dev), 6 (prod), extensible
- **Query complexity**: Handles up to 5-table joins
- **Cost per query**: <$0.001 (Gemini API) - 33% reduction after combining LLM calls
- **LLM calls per query**: 2 (down from 3) - SQL generation + combined analysis/viz
- **Lines of code**: ~3,000 (backend), ~1,500 (frontend)

