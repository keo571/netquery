# Mixed Query Handling + State Simplification - 2025-11-23

## Changes Made

### 1. Removed Redundant `cached_sql` Field

**Problem:** State had both `cached_sql` and `generated_sql` storing the same SQL.

**Before:**
```python
# state.py
cached_sql: Optional[str]  # Cached SQL (if cache hit)
generated_sql: str  # Final SQL used throughout pipeline

# cache_lookup.py
return {
    "cached_sql": cached_sql,  # Redundant!
    "generated_sql": cached_sql,
    "cache_hit_type": "full"
}
```

**After:**
```python
# state.py
generated_sql: str  # Final SQL used throughout pipeline (from cache or generator)

# cache_lookup.py
return {
    "generated_sql": cached_sql,
    "cache_hit_type": "full"  # This flag indicates cache hit
}
```

**Benefit:**
- ✅ Simpler state (one source of truth for SQL)
- ✅ `cache_hit_type` flag indicates origin
- ✅ Less memory usage
- ✅ Clearer semantics

---

### 2. Fixed Mixed Query Handling

**Problem:** Mixed queries (e.g., "What is DNS? Show all DNS records") went through the pipeline, but the general answer wasn't displayed!

**Before:**
```python
# Intent classifier extracts:
{
    "intent": "mixed",
    "sql_query": "Show all DNS records",  # Goes to pipeline
    "general_answer": "DNS is..."  # Stored but never shown! ❌
}

# Interpreter only showed SQL results
# User never sees the "What is DNS?" answer!
```

**After:**
```python
# Interpreter now prepends general_answer for mixed queries

# _create_simple_response() and _create_full_response():
general_section = ""
if state.get("general_answer"):
    general_section = f"## Answer\n\n{state['general_answer']}\n\n---\n\n"

formatted_response = f"{general_section}{sql_section}{results_section}..."
```

**Example Output:**

Input: "What is DNS? Show all DNS records"

**Before (missing general answer):**
```markdown
## SQL Query
SELECT * FROM dns_records

## Results
| name | type | value |
| ... | ... | ... |
```

**After (complete response):**
```markdown
## Answer

DNS (Domain Name System) is a hierarchical naming system that translates human-readable domain names into IP addresses...

---

## SQL Query
SELECT * FROM dns_records

## Results
| name | type | value |
| ... | ... | ... |
```

**Benefit:**
- ✅ Users get complete answers for mixed queries
- ✅ General knowledge + data in one response
- ✅ No wasted LLM work (answer already generated in intent classifier)

---

## Workflow for Mixed Queries

```
User: "What is DNS? Show all DNS records"

1. Intent Classifier (intent_classifier_node)
   ├─ Extract: "What is DNS? Show all DNS records"
   └─ LLM classify_intent():
      {
        "intent": "mixed",
        "sql_query": "Show all DNS records",
        "general_answer": "DNS is a hierarchical naming system..."
      }

2. Cache Lookup → Schema → SQL Generator → Validator → Executor
   └─ Processes: "Show all DNS records"
   └─ Generates SQL: SELECT * FROM dns_records
   └─ Executes and gets results

3. Interpreter (interpreter_node)
   ├─ Checks: state.get("general_answer") → "DNS is..."
   ├─ Prepends general answer section
   └─ Formats complete response:
      ## Answer
      DNS is...

      ---

      ## SQL Query
      SELECT * FROM dns_records

      ## Results
      ...
```

**Key insight:** The general answer is answered ONCE (in intent classifier), stored in state, then displayed by interpreter. Efficient!

---

## Files Modified

### Modified (3 files)

1. **[src/text_to_sql/pipeline/state.py](src/text_to_sql/pipeline/state.py#L39-L43)**
   - Removed `cached_sql: Optional[str]` field
   - Now only `generated_sql` holds the SQL (from cache or generator)

2. **[src/text_to_sql/pipeline/nodes/cache_lookup.py](src/text_to_sql/pipeline/nodes/cache_lookup.py#L63-L85)**
   - Removed `"cached_sql": cached_sql` from return dict
   - Only sets `"generated_sql": cached_sql`

3. **[src/text_to_sql/pipeline/nodes/interpreter.py](src/text_to_sql/pipeline/nodes/interpreter.py)**
   - Added `general_section` to `_create_simple_response()` (lines 113-116)
   - Added `general_section` to `_create_full_response()` (lines 168-171)
   - Prepends general answer with separator for mixed queries

---

## Impact

### Code Quality
- **Removed**: 1 redundant state field
- **Fixed**: Mixed query general answers now displayed
- **Simplified**: State object cleaner

### User Experience
- ✅ Mixed queries now show complete answers
- ✅ Example: "What is X? Show Y" → Gets definition + data
- ✅ More useful for learning queries

### Performance
- Neutral (no change to LLM calls)
- Slightly less memory (one fewer field in state)

---

## Testing Recommendations

### Test Case 1: Pure SQL Query
```
Input: "Show all servers"
Expected:
- No general_section
- Only SQL + results shown
```

### Test Case 2: General Query
```
Input: "What is a load balancer?"
Expected:
- No SQL pipeline
- Only general answer shown
- final_response set by intent_classifier
```

### Test Case 3: Mixed Query (Key Test!)
```
Input: "What is DNS? Show all DNS records"
Expected:
## Answer

DNS (Domain Name System) is...

---

## SQL Query
SELECT * FROM dns_records

## Results
[table of DNS records]
```

### Test Case 4: Cache Hit
```
Input: "Show all servers" (previously cached)
Expected:
- cache_hit_type: "full"
- generated_sql: [cached SQL]
- cached_sql field: Does not exist ✅
```

---

## Breaking Changes

**None!** All changes are internal.

External API unchanged:
- State still has `generated_sql`
- Output format improved (mixed queries now complete)

---

## Related Issues Fixed

This addresses:
- **Q2**: "Why do I have two cached_sql?" → Now only one `generated_sql`
- **Q1**: "Should we separate mixed queries?" → General answer now displayed!

---

## Key Decisions

### Why remove cached_sql instead of keeping for debugging?

**Reason**: The `cache_hit_type` flag provides the same information:
- `cache_hit_type == "full"` → SQL came from cache
- `cache_hit_type == None` → SQL generated fresh

We don't need both. Simpler is better!

### Why not skip SQL pipeline for mixed queries?

**Reason**: The `sql_query` field from intent classifier is **natural language** ("Show all DNS records"), not SQL (`SELECT * FROM dns_records`). We still need:
1. Schema analysis to find relevant tables
2. SQL generation to create actual SQL
3. Validation to ensure safety
4. Execution to get results

Only the **general knowledge part** is answered immediately. The SQL part still goes through the pipeline.

---

## Summary

**Q1: Should we separate mixed queries?**
✅ Fixed! General answer now displayed at the top of mixed query responses.

**Q2: Why two cached_sql fields?**
✅ Simplified! Removed `cached_sql`, only `generated_sql` remains.

Both issues resolved with minimal code changes, better UX, and cleaner state!
