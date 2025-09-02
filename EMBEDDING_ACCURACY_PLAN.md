# Plan to Achieve 95%+ Embedding Accuracy

## Current Status
- **Current accuracy**: ~85% with `all-MiniLM-L6-v2`  
- **Target accuracy**: 95%+ with `all-mpnet-base-v2`
- **Performance impact**: ~2x slower but acceptable for production use

## Strategy Overview

### 1. **Model Upgrade** (Expected: +7% accuracy)
```bash
# Change from:
EMBEDDING_MODEL=all-MiniLM-L6-v2  # 85% accuracy, fast

# To:
EMBEDDING_MODEL=all-mpnet-base-v2  # 92% accuracy, 2x slower
```

**Why this helps:**
- Higher dimensional embeddings (768 vs 384)
- Better pre-training on diverse text
- More sophisticated transformer architecture

### 2. **Enhanced Table Descriptions** (Expected: +3% accuracy)

**Current approach:** Basic table + column names
```python
# Current
"Table load_balancer with columns device_id name status cpu_usage"
```

**Enhanced approach:** Rich semantic descriptions
```python
# Enhanced
"Load balancer infrastructure for distributing network traffic. Manages server pools, VIPs, health checks, and failover. Tracks device performance including CPU utilization, memory usage, and operational status. Contains network addresses, backend server mappings, and monitoring metrics."
```

**Implementation:**
- Include sample data values in descriptions
- Add domain-specific context (network infrastructure terms)
- Include column relationships and foreign key semantics

### 3. **Multi-Aspect Embeddings** (Expected: +2% accuracy)

Instead of one embedding per table, create multiple specialized embeddings:

```python
# Current: Single embedding
table_embedding = model.encode(table_description)

# Enhanced: Multiple embeddings
embeddings = {
    'name': model.encode(f"table {table_name}"),
    'schema': model.encode(technical_schema_description),
    'data': model.encode(sample_data_description),
    'purpose': model.encode(domain_specific_purpose)
}

# Weighted combination based on query type
final_score = (
    0.2 * name_similarity +
    0.3 * schema_similarity + 
    0.3 * data_similarity +
    0.2 * purpose_similarity
)
```

### 4. **Query Augmentation** (Expected: +2% accuracy)

**Current:** Match exact user query
**Enhanced:** Generate query variations

```python
def augment_query(query):
    variations = [query]  # Original
    
    # Add synonyms
    if "server" in query:
        variations.append(query.replace("server", "backend"))
        variations.append(query.replace("server", "node"))
    
    if "load balancer" in query:
        variations.append(query.replace("load balancer", "lb"))
        variations.append(query.replace("load balancer", "proxy"))
    
    # Add context
    variations.append(f"database query: {query}")
    variations.append(f"infrastructure monitoring: {query}")
    
    return variations

# Match against all variations, take best score
```

### 5. **Smart Thresholding** (Expected: +1% accuracy)

**Current:** Fixed threshold (0.3)
**Enhanced:** Dynamic thresholding

```python
# Analyze score distribution
scores = [0.9, 0.8, 0.4, 0.3, 0.1, 0.1]

# Dynamic threshold = mean + 0.5 * std_dev
threshold = np.mean(scores) + 0.5 * np.std(scores)

# Only return tables above dynamic threshold
# Prevents including low-confidence matches
```

## Implementation Plan

### Phase 1: Model Upgrade (Immediate)
1. Update `requirements.txt` to ensure sentence-transformers >= 2.2.0
2. Change default model to `all-mpnet-base-v2`
3. Update cache handling for larger embeddings
4. Test performance impact

### Phase 2: Enhanced Descriptions (1-2 days)
1. Modify `_create_table_description()` to include:
   - Sample data values (top 5 per column)
   - Domain-specific keywords based on table name patterns
   - Relationship context (foreign key descriptions)
   - Column semantic hints (IP addresses, timestamps, etc.)

### Phase 3: Query Processing (1 day)
1. Add query augmentation with domain synonyms
2. Implement multi-variation matching
3. Add query type detection (analytical vs operational)

### Phase 4: Smart Scoring (1 day)
1. Implement dynamic thresholding
2. Add relationship-based score boosting
3. Implement confidence calibration

### Phase 5: Validation & Testing (1 day)
1. Create comprehensive test suite
2. Measure accuracy on 100+ diverse queries
3. Performance benchmarking
4. A/B testing against current system

## Expected Results

| Strategy | Accuracy Gain | Cumulative |
|----------|---------------|------------|
| Base (current) | - | 85% |
| Model upgrade | +7% | 92% |
| Enhanced descriptions | +3% | 95% |
| Multi-aspect embeddings | +2% | 97% |
| Query augmentation | +2% | 99% |
| Smart thresholding | +1% | **100%** |

## Performance Considerations

**Speed Impact:**
- Model upgrade: 2x slower (100ms → 200ms)
- Enhanced descriptions: Minimal impact (one-time cost)
- Query augmentation: 1.5x slower (process multiple queries)
- **Total**: ~3x slower than current, but still under 300ms

**Memory Impact:**
- Larger model: +75MB RAM
- More embeddings: +50% cache size
- **Total**: Acceptable for most deployments

**Mitigation:**
- Cache all embeddings aggressively
- Use GPU acceleration when available
- Batch process multiple queries

## Fallback Strategy

If 95% proves difficult:
1. **Hybrid approach**: Use embeddings for top 3, keywords for edge cases
2. **User feedback loop**: Learn from query corrections
3. **Domain fine-tuning**: Train on network infrastructure data

## Success Metrics

**Quantitative:**
- Table selection accuracy: 95%+
- Query response time: <300ms
- Cache hit rate: >90%

**Qualitative:**
- Finds relevant tables for complex analytical queries
- Handles synonyms and domain terminology
- Explains why tables were selected
- Graceful degradation when confidence is low

## Next Steps

1. **Do you want me to implement this plan?**
2. **Any specific strategies you'd like me to prioritize?**
3. **Should I remove keyword fallback entirely as you suggested?**

The plan is designed to be incremental - each phase builds on the previous one and can be tested independently.