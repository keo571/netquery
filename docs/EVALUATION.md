# Netquery Query Evaluation Framework

This document describes the comprehensive evaluation system for testing and validating the Netquery text-to-SQL pipeline using `scripts/evaluate_queries.py`.

## Purpose

The Query Evaluation framework tests the complete text-to-SQL pipeline end-to-end, measuring technical success across different query types and complexity levels.

### What It Tests

#### Query Categories (Aligned with SAMPLE_QUERIES.md)

1. **Basic Queries** - Simple table queries and filtering
   - "Show me all load balancers"
   - "List servers in maintenance"
   - "What SSL certificates do we have?"

2. **Analytics & Aggregations** - Counting, statistics, performance metrics
   - "How many load balancers do we have?"
   - "What's the average CPU utilization by datacenter?"
   - "Count servers by status"

3. **Multi-Table Joins** - Complex relationships and filtering
   - "Show load balancers with their backend servers"
   - "List unhealthy load balancers with high CPU servers"

4. **Time-Series & Visualization** - Charts and trend analysis
   - "Show network traffic trends over time"
   - "Display load balancer health scores over time"

5. **Troubleshooting** - Current status and problem identification
   - "Show certificates expiring in 30 days"
   - "Which servers have connection issues?"

6. **Edge Cases & Error Handling** - Invalid queries and safety validation
   - "Delete all servers" (should be blocked)
   - "Show me nonexistent table data"

### Metrics

#### Technical Success Rate
Percentage of queries that execute successfully through the entire pipeline:
```
Technical Success Rate = (Successful Queries / Total Queries) × 100%
```


### Pipeline Stage Tracking

Each query is evaluated through all pipeline stages:

| Stage | Success Indicator | What It Measures |
|-------|------------------|------------------|
| **Schema** | ✅/❌ | Schema analysis and table selection |
| **SQL** | ✅/❌ | SQL query generation |
| **Execution** | ✅/❌ | Query execution and result retrieval |
| **Charts** | Type/None | Automatic chart generation |

### Output

- **Console Report** - Real-time progress and summary statistics
- **HTML Report** - Detailed results table saved to `testing/evaluations/query_evaluation_report.html`

### Usage

```bash
# Run complete evaluation
python scripts/evaluate_queries.py

# Check GEMINI_API_KEY is set
export GEMINI_API_KEY=your_key_here
python scripts/evaluate_queries.py
```

**Example Output:**
```
🚀 Starting Netquery Evaluation...
📊 Testing 52 queries across 6 categories

📂 Basic Queries (8 queries)
   1. Testing: Show me all load balancers
      ✅ SUCCESS (1.2s, 8 rows)
   
📈 EVALUATION SUMMARY
Technical Success Rate: 45/52 (86.5%)
Charts Generated: 12
```

## Integration with Development

### Pre-commit Hooks
```bash
# Add to .git/hooks/pre-commit
python scripts/evaluate_queries.py
if [ $? -ne 0 ]; then
    echo "Query evaluation failed"
    exit 1
fi
```

### CI/CD Pipeline
```yaml
# Add to GitHub Actions
- name: Run Query Evaluation
  run: python scripts/evaluate_queries.py
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

### Performance Monitoring
- Track success rates over time
- Monitor query execution times
- Identify performance regressions
- Benchmark new features

---

## Files and Locations

- **Query Evaluation Script**: `scripts/evaluate_queries.py`
- **Test Queries**: Defined in `docs/SAMPLE_QUERIES.md`
- **Reports**: Saved to `testing/evaluations/`
- **Configuration**: Uses `.env` for API keys

## Future Improvements

### Technical Success Rate Improvements

**Difficulty-Based LLM Selection**
- Use advanced LLMs (GPT-4, Claude-3.5) for high-complexity queries identified by query planner
- Keep standard LLM (Gemini) for simple queries to optimize costs

**Schema Analysis Enhancement** 
- Upgrade embedding model from `all-MiniLM-L6-v2` to `text-embedding-3-large`
- Add hybrid search combining semantic similarity with BM25 scoring (BM25 provides lexical matching for exact technical terms while embeddings handle conceptual understanding)
- Enhance table descriptions with infrastructure-specific keywords

**SQL Generation Resilience**
- Implement SQL validation with retry using increased reasoning levels
- Add few-shot learning with curated network infrastructure examples
- Automatic query optimization (LIMIT clauses, execution time controls)

### Error Recovery and Reliability

**Smart Error Recovery**
- Query decomposition for overly complex requests
- Intelligent fallback to simpler query variants when complex joins fail
- Better error messages with suggested alternatives

**Learning System**
- Track query success patterns to improve complexity assessment
- Log execution failures to identify common problem areas
- Adaptive difficulty scoring based on historical performance

### Measurement Enhancements

**Additional Metrics**
- Complex query success rate (difficulty > 0.8)
- Average query execution time by complexity level
- Schema analysis accuracy by table type
- Failure mode categorization (syntax, logic, timeout, safety)

The query evaluation framework ensures Netquery maintains high quality and reliability across all text-to-SQL use cases and deployment scenarios.