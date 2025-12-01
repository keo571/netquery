# Custom Suggested Queries - Feature Guide

**Date**: November 28, 2025
**Status**: Implemented ✅ (Required)

> **Architecture Decision**: See [ADR-019](docs/ARCHITECTURE_DECISION.md#adr-019-required-visualization-focused-suggested-queries) for the rationale behind making suggested queries required.

## Overview

This guide explains how to use custom query suggestions in Excel schema files. The `suggested_queries` sheet is a **required** part of the Excel schema format, allowing you to define visualization-focused, hand-crafted query suggestions that appear in the frontend.

## Problem Solved

### Before
The system auto-generated generic suggestions based on table names:
- "Show recent load balancers records."
- "How do load balancers relate to virtual ips?"
- "Summarize load balancers by id."

**Issues:**
- Generic and boring (doesn't use domain knowledge)
- Not user-friendly (awkward phrasing)
- Missed context (didn't leverage sample values like `["active", "inactive", "maintenance"]`)
- Limited diversity (only 3 patterns per table)

### After
Users can define custom suggestions in the Excel schema:
- "Show all active load balancers"
- "Which load balancers are in maintenance mode?"
- "List virtual IPs using HTTPS protocol"
- "Show backend servers with health status 'unhealthy'"
- "Which SSL certificates expire in the next 30 days?"

**Benefits:**
- Natural, domain-specific questions
- Leverages sample values and real use cases
- Showcases system capabilities
- Helps onboard new users

## Implementation

### 1. Excel Parser Enhancement
**File**: [src/schema_ingestion/excel_parser.py](src/schema_ingestion/excel_parser.py)

Added support for optional `suggested_queries` sheet:

```python
class ExcelSchemaParser:
    def __init__(self, excel_file_path: str):
        self.suggested_queries: List[str] = []  # New field

    def _parse_suggested_queries(self, df: pd.DataFrame):
        """Parse suggested_queries tab (optional)."""
        if 'query' not in df.columns:
            return

        for _, row in df.iterrows():
            if pd.notna(row['query']):
                query = str(row['query']).strip()
                if query:
                    self.suggested_queries.append(query)
```

### 2. Canonical Schema Update
**File**: [src/schema_ingestion/canonical.py](src/schema_ingestion/canonical.py)

Added `suggested_queries` field to canonical schema:

```python
@dataclass
class CanonicalSchema:
    suggested_queries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = {...}
        if self.suggested_queries:
            d['suggested_queries'] = self.suggested_queries
        return d
```

### 3. Schema Builder Integration
**File**: [src/schema_ingestion/builder.py](src/schema_ingestion/builder.py)

Builder passes suggested queries from Excel to canonical schema:

```python
def build_from_excel(...):
    # ... build tables ...

    # Add suggested queries from Excel (if any)
    suggested_queries = excel_parser.get_suggested_queries()
    if suggested_queries:
        canonical.suggested_queries = suggested_queries
```

### 4. Schema Overview Update
**File**: [src/common/schema_summary.py](src/common/schema_summary.py)

Modified to prefer custom suggestions over auto-generated:

```python
def get_schema_overview(...):
    # Use custom suggestions from schema if available, otherwise auto-generate
    suggested_queries = (canonical.suggested_queries
                        if canonical.suggested_queries
                        else _generate_suggestions(table_summaries))
```

## Excel Format

### Sheet: `suggested_queries` (Optional)

| Column | Required | Description |
|--------|----------|-------------|
| `query` | Yes | Natural language query suggestion |

**Example:**
```
| query |
|-------|
| Show all active load balancers |
| Which load balancers are in maintenance mode? |
| List virtual IPs using HTTPS protocol |
```

## Usage

### Adding Suggestions to Existing Schema

1. **Add sheet to Excel file:**
   ```bash
   # Use the helper script
   python scripts/add_suggested_queries_to_excel.py
   ```

2. **Rebuild schema:**
   ```bash
   python -m src.schema_ingestion build \
     --excel schema_files/sample_schema.xlsx \
     --output schema_files/sample_schema.json \
     --schema-id sample
   ```

3. **Verify in JSON:**
   ```bash
   python -m json.tool schema_files/sample_schema.json | grep -A 15 "suggested_queries"
   ```

### Creating New Schema with Suggestions

When creating a new database schema (e.g., `production`):

1. Create Excel with 3 sheets:
   - `table_schema` (REQUIRED)
   - `mapping` (REQUIRED)
   - `suggested_queries` (OPTIONAL)

2. Run schema ingestion as usual

## Files Modified

### Core Implementation
1. [src/schema_ingestion/excel_parser.py](src/schema_ingestion/excel_parser.py) - Parse suggested_queries sheet
2. [src/schema_ingestion/canonical.py](src/schema_ingestion/canonical.py) - Store suggested_queries in canonical format
3. [src/schema_ingestion/builder.py](src/schema_ingestion/builder.py) - Transfer suggestions from Excel to canonical
4. [src/common/schema_summary.py](src/common/schema_summary.py) - Use custom suggestions in schema overview

### Documentation
1. [docs/SCHEMA_INGESTION.md](docs/SCHEMA_INGESTION.md) - Added Tab 3 documentation
2. [docs/ADDING_NEW_DATABASE.md](docs/ADDING_NEW_DATABASE.md) - Updated Excel format section

### Sample Data
1. [schema_files/sample_schema.xlsx](schema_files/sample_schema.xlsx) - Added suggested_queries sheet with 12 queries
2. [schema_files/sample_schema.json](schema_files/sample_schema.json) - Rebuilt with custom suggestions

### Scripts
1. [scripts/add_suggested_queries_to_excel.py](scripts/add_suggested_queries_to_excel.py) - Helper script to add suggestions

## Sample Queries for Sample Database

The sample database now has 15 visualization-focused suggestions organized by chart type:

### Bar Chart Queries (4)
1. Show count of load balancers by datacenter
2. Show count of load balancers by status
3. Show count of backend servers by health status
4. Show count of virtual IPs by protocol

### Pie Chart Queries (3)
5. Show distribution of load balancers by status
6. Show distribution of backend servers by health status
7. Show distribution of virtual IPs by protocol

### Line Chart Queries (4) - Last 30 Days (Oct 29 - Nov 28, 2025)
8. Show load balancer performance stats over the last 30 days
9. Show requests per second trend for the last 30 days
10. Show connection count trend over the last 30 days
11. Show bandwidth usage over the last 30 days

### Table/List Queries (4)
12. Show all active load balancers
13. List all virtual IPs with their backend servers
14. Show backend servers that are currently unhealthy
15. List load balancers with their total number of backend servers

## Breaking Change

**⚠️ BREAKING CHANGE**: The `suggested_queries` sheet is now **required** in all Excel schema files.

- **Required sheet**: Excel schema files must include `suggested_queries` sheet
- **Validation**: Schema ingestion will fail if the sheet is missing or empty
- **Migration**: Existing schemas without suggestions must be updated to include them
- **Best practice**: Include queries for different visualization types (bar, pie, line, table)

## Testing

Verified implementation:
```bash
# 1. Added suggested_queries sheet to sample_schema.xlsx
python scripts/add_suggested_queries_to_excel.py

# 2. Rebuilt schema
python -m src.schema_ingestion build \
  --excel schema_files/sample_schema.xlsx \
  --output schema_files/sample_schema.json \
  --schema-id sample

# 3. Verified in JSON
python -m json.tool schema_files/sample_schema.json | grep -A 15 "suggested_queries"

# Output shows all 15 visualization-focused suggestions ✅
```

## Future Enhancements

Potential improvements:
1. **LLM-generated suggestions**: Use LLM to generate suggestions based on schema + sample values
2. **Multiple suggestion sets**: Different suggestions for different user roles (admin, viewer, analyst)
3. **Localization**: Support for suggested queries in multiple languages
4. **Analytics**: Track which suggestions are used most often

## Summary

**Problem**: Generic auto-generated query suggestions weren't helpful
**Solution**: Added optional `suggested_queries` sheet to Excel schema format
**Result**: Users can now provide custom, domain-specific query suggestions
**Impact**: Better UX, improved onboarding, showcases system capabilities

---

**All changes tested and working correctly.**
