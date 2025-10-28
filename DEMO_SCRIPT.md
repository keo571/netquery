# Netquery Live Demo Script

## Pre-Demo Setup (5 minutes before presentation)

### 1. Start Backend Server
```bash
cd /Users/qiyao/Code/netquery
./start-dev.sh
# Wait for: "Uvicorn running on http://127.0.0.1:8000"
```

### 2. Start Frontend Adapter
```bash
cd /Users/qiyao/Code/netquery-insight-chat
python netquery_server.py
# Wait for: "Uvicorn running on http://0.0.0.0:8001"
```

### 3. Start Frontend UI
```bash
cd /Users/qiyao/Code/netquery-insight-chat
npm start
# Browser should open to http://localhost:3000
```

### 4. Verify Setup
- [ ] Frontend loads with welcome message
- [ ] Schema overview shows tables
- [ ] Test query: "Show all load balancers" works

---

## Demo Flow (10 minutes)

### Introduction (30 seconds)
**Say:**
"Today I'll demonstrate Netquery, our AI-powered text-to-SQL system. I'll ask questions in plain English, and the system will automatically query our infrastructure database and visualize the results. Let's start simple and build up to more complex queries."

---

### Query 1: Simple Table Lookup (1 min)
**Objective:** Show basic functionality

**Type:**
```
Show me all load balancers
```

**What to highlight:**
- ✓ Clean table output
- ✓ Fast response time (1-2 seconds for data, 4-5 seconds total)
- ✓ Pagination controls
- ✓ Column headers match database

**Say:**
"Notice it returned a clean table with all our load balancers. The system automatically formatted the output and added pagination. Let's try something more specific."

**Expected Output:**
- Table with columns: ID, Name, IP Address, Status, Datacenter, Created At
- Multiple rows with load balancers
- Status values: active, inactive, maintenance
- Datacenters: Various datacenter locations

---

### Query 2: Relationship Query (1.5 min)
**Objective:** Show table joins and relationships

**Type:**
```
Show each virtual IP with its associated load balancer
```

**What to highlight:**
- ✓ Automatic join between virtual_ips and load_balancers tables
- ✓ Displays both VIP details and LB information
- ✓ Shows the relationship clearly

**Follow-up (show conversational context):**
```
Which of these use HTTPS protocol?
```

**Say:**
"Notice I didn't have to repeat 'virtual IPs' - the system remembers the context from my previous question. This is the conversational aspect at work. Now it's filtering the previous results for HTTPS."

**Expected Output:**
- First query: Table showing VIP Address, Port, Protocol, Pool Name, Load Balancer Name, Datacenter
- Second query: Filtered subset showing only HTTPS virtual IPs

---

### Query 3: Aggregation + Visualization (2 min)
**Objective:** Show aggregation and automatic charting

**Type:**
```
Count load balancers per datacenter
```

**What to highlight:**
- ✓ Automatic GROUP BY aggregation
- ✓ **Auto-generated bar chart** ⭐ KEY FEATURE
- ✓ Both table and chart views
- ✓ Clear distribution visualization

**Say:**
"Here's where it gets interesting. The system not only aggregated the data across datacenters but also detected that this would work well as a bar chart. Notice both the table and the visualization - no manual chart configuration needed."

**Point to chart:**
"The X-axis shows datacenters, Y-axis shows the count. This makes it immediately clear which datacenters have the most load balancers deployed."

**Technical note (if asked):**
"We recently optimized this - the analysis and visualization are now generated in a SINGLE LLM call instead of two separate calls. This reduced response time by 33% and cut API costs by 33%."

**Expected Output:**
- Table: Datacenter | Count
- Bar chart with bars for each datacenter
- Clear distribution pattern visible

---

### Query 4: Health Status Monitoring (2.5 min)
**Objective:** Show filtering for operational monitoring

**Type:**
```
Which backend servers in us-east-1 have unhealthy status?
```

**What to highlight:**
- ✓ Multiple filter conditions (location AND status)
- ✓ Operational monitoring use case
- ✓ Practical for on-call engineers

**Say:**
"This is a real operational query - something an on-call engineer would ask. The system understood we need to filter by both datacenter and health status. In a traditional setup, they'd need to write a WHERE clause with multiple conditions."

**Optional Follow-up:**
```
Show me their associated load balancers
```

**Say:**
"Now we're adding context - which load balancers are affected by these unhealthy servers? The system remembers we're talking about those specific unhealthy servers."

**Expected Output:**
- Table: Hostname, IP Address, Port, Pool Name, Health Status, Datacenter
- Filtered to us-east-1 AND health_status = 'down' or 'unknown'
- Follow-up adds load balancer information via join

---

### Query 5: Time-Series Analysis (2.5 min)
**Objective:** Show time-series and line chart generation

**Type:**
```
Show traffic stats from the past 24 hours
```

**What to highlight:**
- ✓ Time-series query
- ✓ **Line chart automatically generated** ⭐ KEY FEATURE
- ✓ Trend analysis visible
- ✓ Understands relative time ("past 24 hours")

**Say:**
"This is a time-series query. Notice the system generated a line chart, perfect for showing trends over time. You can see traffic patterns - requests per second, bytes transferred, active connections. This helps identify anomalies or capacity planning needs. The analysis and chart appear together because we optimized the system to generate both in a single AI call."

**Optional - Export CSV:**
- Click "Download CSV" button
- Show downloaded file in Finder
- "You can export data for further analysis in Excel or other tools"

**Expected Output:**
- Table: Virtual IP ID | Timestamp | Requests/Sec | Bytes In | Bytes Out | Active Connections
- Line chart with time on X-axis, metrics on Y-axis
- 24 hours worth of data points

---

### Query 6: Complex Multi-Table Query (1.5 min)
**Objective:** Show system handling complex joins across multiple tables

**Type:**
```
Show the complete path from wide IP to backend servers
```

**What to highlight:**
- ✓ Five-table join (wide_ips → wide_ip_pools → virtual_ips → load_balancers → backend_servers)
- ✓ Complete hierarchy visualization
- ✓ Shows global load balancing architecture

**Say:**
"This is the most complex query - it traverses the entire global load balancing hierarchy. Starting from DNS (wide IPs), through virtual IPs, down to the physical backend servers. This requires joining 5 tables together. In traditional SQL, this would take an experienced DBA considerable time to write correctly."

**Point to the results:**
"You can see the complete path: Wide IP domain name → Virtual IP address → Load Balancer → Backend Server. This gives you the full picture of your global traffic routing."

**Expected Output:**
- Table: Wide IP Domain | LB Method | VIP Address | Port | LB Name | Datacenter | Backend Hostname | Backend IP | Health Status
- Multiple rows showing the complete routing hierarchy
- Demonstrates the full complexity the system can handle

---

## Bonus Demonstrations (If Time Permits)

### Bonus 0: Schema Ingestion Tool (Production Readiness)
**Objective:** Show how Netquery works with incomplete production databases

**Context:**
"Before we wrap up, let me show you what makes Netquery production-ready - not just a development toy. Most production databases have problems that break text-to-SQL systems."

**Problem Setup:**
```bash
# Open terminal and show production database issues
cd /Users/qiyao/Code/netquery

# Show that production databases often lack foreign keys
cat <<EOF
Common Production Issues:
1. No foreign key constraints (removed for performance)
2. Cryptic table/column names (lb_cfg, bs_pool)
3. No documentation or descriptions
4. These break AI table discovery and JOIN generation
EOF
```

**Solution Demo:**
```bash
# Show the schema ingestion tool
python -m src.schema_ingestion --help

# Command outputs:
# Commands:
#   build     - Build canonical schema from database or Excel
#   validate  - Validate schema correctness
#   summary   - Show schema overview
#   diff      - Compare two schemas
```

**Show Development Path (Automatic):**
```bash
# For databases WITH foreign keys - fully automatic
python -m src.schema_ingestion build \
  --output schema_files/dev_schema.json

# Say: "This extracted all tables, columns, foreign keys, and types automatically"
# Say: "Works great for SQLite, MySQL with proper constraints"
```

**Show Production Path (Excel-Based):**
```bash
# For databases WITHOUT foreign keys - use Excel definitions
ls schema_files/prod_schema.xlsx

# Say: "For production, we create an Excel file with 2 tabs:"
# Say: "Tab 1: table_schema - human descriptions of tables and columns"
# Say: "Tab 2: mapping - explicit foreign key relationships"

python -m src.schema_ingestion build \
  --excel schema_files/prod_schema.xlsx \
  --output schema_files/prod_schema.json \
  --schema-id prod

# Say: "Now the system knows how to join tables and what they mean"
```

**Show Schema Summary:**
```bash
# View what was built
python -m src.schema_ingestion summary schema_files/prod_schema.json -v

# Expected output shows:
# - 6 tables (load_balancers, virtual_ips, etc.)
# - 8 relationships
# - All with human-readable descriptions
```

**Show Schema Validation:**
```bash
# Validate schema correctness
python -m src.schema_ingestion validate schema_files/prod_schema.json

# Say: "This catches errors before deployment"
```

**Show Schema Comparison:**
```bash
# Compare schemas to see evolution
python -m src.schema_ingestion diff \
  schema_files/dev_schema.json \
  schema_files/prod_schema.json

# Say: "This helps track schema changes over time"
# Say: "Critical for safe migrations"
```

**Key Points to Emphasize:**
- ✅ "This solves the 'last mile' problem - going from POC to production"
- ✅ "Excel file is a one-time setup, then queries work forever"
- ✅ "No database changes needed - we adapt to YOUR database"
- ✅ "Same query code works on dev and prod - just point to different schema files"
- ✅ "Version control the Excel + JSON files alongside your code"

**Say:**
"This is what makes Netquery universal. It's not limited to perfect development databases. We've built tooling to handle the messy reality of production systems."

**Time:** 3-4 minutes

---

### Bonus 1: Conversational Follow-Up
After any query, type:
```
Show me more details about the top result
```

**Say:** "The system remembers context and understands pronouns like 'top result'"

---

### Bonus 2: Wide IP Global Load Balancing
```
Show all wide IPs and their load balancing algorithms
```

**Expected:** Table showing domain names with their LB methods (round-robin, geo, ratio)

**Say:** "Wide IPs are for global DNS load balancing. The system understands this specialized concept and knows which table and columns to query."

---

### Bonus 3: Chart Type Variation
```
Count backend servers by health status
```

**Expected:** Pie chart (if system detects categorical distribution) or Bar chart

**Say:** "Notice this generated a pie/bar chart - the system detected this is distribution data showing healthy vs unhealthy servers."

---

### Bonus 4: Advanced Analytics
```
Show datacenters with more than 5 load balancers
```

**Expected:** Aggregation with HAVING clause

**Say:** "This requires a HAVING clause in SQL - filtering on aggregated results, not raw data. The system understood the distinction and generated the correct SQL."

---

## Handling Q&A During Demo

### If Asked: "Can I see the SQL?"
**Response:**
"Great question! In the current UI, the SQL is logged in the backend. Let me show you the architecture - the SQL Generator component takes your question and creates the query. We can add a 'Show SQL' toggle in the UI for transparency."

**Action:** Show [sql_generator.py](src/text_to_sql/pipeline/nodes/sql_generator.py) briefly

---

### If Asked: "What if it generates wrong SQL?"
**Response:**
"Excellent question. The system has retry logic built-in - if the first SQL fails, it tries up to 3 times with adjusted prompts. Also, the validator checks for dangerous operations before execution. Let me show you..."

**Action:** Intentionally type a vague query to show retry behavior

---

### If Asked: "How does it know which tables to use?"
**Response:**
"Great question! It's actually a two-phase process - semantic search plus smart FK expansion..."

**Action:** Draw diagram on whiteboard or show Slide 4 from presentation:
```
PHASE 1: SEMANTIC SEARCH
  Your question → Vector embedding
  All table descriptions → Vector embeddings
  System finds closest matches (semantic similarity)
  Top 5 tables selected (e.g., customers, orders)

PHASE 2: SMART FK EXPANSION
  For each of the 5 semantic tables:
    • Find OUTBOUND foreign keys (tables it joins to)
    • Find INBOUND foreign keys (tables that join to it)
    • Prioritize by relevance score
    • Cap at 15 total tables (prevents token explosion)

  Example: customers (5) + orders (5)
           → expands to 12 tables (addresses, payments, order_items, etc.)
```

**Say:** "It's like Google search but for database tables - finds relevant tables semantically, then automatically includes related tables that might be needed for JOINs. We use smart limits to prevent it from pulling in the entire database - only the most relevant 15 tables max."

**Technical note if pressed:**
"The expansion prioritizes OUTBOUND foreign keys first because those are more likely to be JOIN targets. We also only include sample data for the 5 semantically matched tables, not the 10 FK-expanded ones. This saves about 3,000 tokens and makes responses 2-3x faster."

---

### If Asked: "Can it modify data?"
**Response:**
"No, and that's by design. The validator explicitly blocks INSERT, UPDATE, DELETE, DROP, and ALTER operations. It's read-only for safety. If you need to modify data, you'd use traditional database tools with proper access controls."

**Action:** Show [validator.py](src/text_to_sql/pipeline/nodes/validator.py) briefly

---

### If Asked: "What's the accuracy rate?"
**Response:**
"In our testing, about 85-90% of queries succeed on the first try. Complex queries with ambiguous wording sometimes need rephrasing. The retry logic handles most edge cases automatically. The more specific your question, the better the results."

---

### If Asked: "How fast is it?"
**Response:**
"The system responds in 4-5 seconds total, but you see the actual data in 1-2 seconds. We use streaming to show results progressively. We recently optimized from 6-8 seconds by combining the analysis and visualization generation into a single AI call instead of two separate calls - that's a 33% improvement in both speed and cost."

---

### If Asked: "Does this work with production databases that lack foreign keys?"
**Response:**
"Absolutely! That's exactly what the Schema Ingestion tool solves. Production PostgreSQL databases often drop foreign key constraints for performance. We handle this with a two-path approach:

Path 1: If your database HAS foreign keys (dev environments), the tool automatically extracts everything.

Path 2: If your database LACKS foreign keys (production), you create a simple Excel file with two tabs - one defining table/column descriptions, another defining the relationships. It's a one-time setup, then queries work forever.

The Excel file becomes your 'source of truth' that you version control alongside your code."

**Action:** Offer to show the Schema Ingestion bonus demo

---

### If Asked: "What if my table names are cryptic?"
**Response:**
"Great question! That's another production reality we handle. The Excel schema file lets you provide human-readable descriptions for every table and column.

For example, if your database has a table called 'lb_cfg', you can describe it as 'Load balancer configuration settings'. The AI uses these descriptions (not the cryptic names) when finding relevant tables for your question.

This is crucial because the semantic search works on meanings, not just table names."

---

### If Asked: "How much does this cost?"
**Response:**
"We use Google Gemini API, which costs about $0.10 per million input tokens. For a typical query, that's less than $0.001 - essentially a fraction of a cent per query. We recently reduced this by 33% by combining two AI calls into one. The productivity gain for engineers who don't know SQL is huge compared to the API cost - even before optimization, costs were negligible."

---

## Post-Demo Wrap-Up (1 min)

**Say:**
"Let me summarize what we've seen:
1. Simple lookups - 'show me all X'
2. Filtering - 'in us-east-1', 'expiring in 30 days'
3. Aggregations - 'average by datacenter'
4. Time-series - 'trends over last 3 days'
5. Complex joins - 'load balancers with their servers'
6. Schema Ingestion - works with ANY database (even incomplete ones)

All without writing a single line of SQL. The system handled table discovery, SQL generation, safety validation, and automatic visualization.

What makes this production-ready is the Schema Ingestion tool. It handles real-world databases that lack foreign keys or have cryptic names - problems that break most text-to-SQL systems. Two-path approach: automatic for complete databases, Excel-based for incomplete ones.

Performance-wise, we're seeing 4-5 second total response times, with data visible in 1-2 seconds. We recently optimized the system to use only 2 AI calls per query instead of 3, reducing both latency and cost by 33%.

The code is available in our repos, and I'm happy to help anyone who wants to try it or adapt it for their use case."

---

## Emergency Fallback Plan

### If Live Demo Completely Fails:

**Option 1: Use Screenshots**
- Have pre-captured screenshots in `/demo_screenshots/` folder
- Walk through each screenshot as if live

**Option 2: Show Recorded Video**
- Pre-record entire demo flow
- Narrate over the video

**Option 3: Code Walkthrough**
- Show architecture slides
- Walk through key source files:
  - [gemini_cli.py](gemini_cli.py) - Entry point
  - [sql_generator.py](src/text_to_sql/pipeline/nodes/sql_generator.py) - LLM interaction
  - [schema_analyzer.py](src/text_to_sql/pipeline/nodes/schema_analyzer.py) - Embedding search

---

## Test Run Checklist

**Run this 1 hour before presentation:**

```bash
# Test each query and record results
echo "Test 1: Show all load balancers"
echo "Test 2: Show each virtual IP with its associated load balancer"
echo "Test 3: Count load balancers per datacenter"
echo "Test 4: Which backend servers in us-east-1 have unhealthy status?"
echo "Test 5: Show traffic stats from the past 24 hours"
echo "Test 6: Show the complete path from wide IP to backend servers"
```

- [ ] All 6 queries return results
- [ ] Charts render correctly for Query 3 and Query 5
- [ ] Analysis and visualization appear together (combined LLM call)
- [ ] No console errors
- [ ] Export CSV works
- [ ] Data visible in < 2 seconds, full response in < 5 seconds per query
- [ ] Query 6 successfully joins all 5 tables

**If any test fails:**
1. Check GEMINI_API_KEY is set
2. Check database has data (`sqlite3 data/infrastructure.db "SELECT COUNT(*) FROM load_balancers;"`)
3. Restart servers
4. Check API quota/rate limits

---

## Timing Guide

| Section | Duration | Cumulative |
|---------|----------|------------|
| Introduction | 0:30 | 0:30 |
| Query 1 (Simple Lookup) | 1:00 | 1:30 |
| Query 2 (Relationship) | 1:30 | 3:00 |
| Query 3 (Aggregation + Chart) | 2:00 | 5:00 |
| Query 4 (Health Monitoring) | 2:30 | 7:30 |
| Query 5 (Time-Series) | 2:30 | 10:00 |
| Query 6 (Complex 5-Table Join) | 2:00 | 12:00 |
| Buffer for questions | 3:00 | 15:00 |

**Total:** 15 minutes with buffer

**Query Response Times (After Optimization):**
- Data visible: 1-2 seconds
- Full response (with analysis + chart): 4-5 seconds
- Previous performance (before combining LLM calls): 6-8 seconds
- **Improvement: 33% faster**

---

## Quick Reference: Demo URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Adapter Server: http://localhost:8001

---

## Presenter Tips

✅ **DO:**
- Speak slowly and clearly
- Pause after each query result to let audience absorb
- Highlight specific UI elements with mouse cursor
- Explain what's happening during load times
- Show enthusiasm about the technology
- Acknowledge limitations honestly

❌ **DON'T:**
- Rush through queries
- Assume audience knows AI terminology
- Skip over visualizations
- Ignore errors (use them as teaching moments)
- Go over time limit
- Use jargon without explanation

---

## Post-Demo Follow-Up Email Template

```
Subject: Netquery Demo - Resources & Next Steps

Hi Team,

Thanks for attending the Netquery demo today! Here are the resources I mentioned:

**Repositories:**
- Backend: /Users/qiyao/Code/netquery
- Frontend: /Users/qiyao/Code/netquery-insight-chat

**Getting Started:**
1. See STARTUP_GUIDE.md for setup instructions
2. Environment variables needed: GEMINI_API_KEY, DATABASE_URL
3. Setup time: ~10 minutes

**Demo Materials:**
- Presentation slides: DEMO_PRESENTATION.md
- Demo script: DEMO_SCRIPT.md
- [Link to demo recording]

**Example Queries to Try:**
- "Show all load balancers"
- "Show each virtual IP with its associated load balancer"
- "Count load balancers per datacenter"
- "Which backend servers are unhealthy?"
- "Show traffic stats from the past 24 hours"
- "Show the complete path from wide IP to backend servers"

**Office Hours:**
I'm available for 1-on-1 demos or to help with setup:
- [Your availability]
- [Booking link or email]

**Feedback Survey:**
[Link to feedback form]

Let me know if you have questions!

[Your Name]
```

---

## Key Metrics to Track After Demo

- Number of attendees
- Questions asked (categorize by: technical, business, cost, security)
- Interest level (survey responses)
- Follow-up requests for setup help
- Adoption by other teams

This helps measure impact and improve future presentations!
