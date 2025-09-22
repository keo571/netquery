# Architecture Decision Document

## Overview
This document outlines the agreed-upon architecture for the Netquery system with React frontend, FastAPI backend, and LLM-powered interpretation.

## Core Principles
- **Simplicity First**: Direct Python calls, no unnecessary abstraction layers
- **Performance Focused**: Minimize data loading and LLM calls
- **User Controlled**: Interpretation is optional, user-triggered
- **Clear Data Limits**: Well-defined boundaries for preview, interpretation, and export

## Architecture Components

### 1. Frontend: React Application
- User interface for query input
- Displays SQL generation results
- Shows data preview (30 rows)
- Triggers interpretation when requested
- Handles CSV download

### 2. Backend: FastAPI Server
- Direct Python imports (no MCP layer)
- Manages query sessions
- Caches data to avoid re-execution
- Handles all LLM interactions

### 3. Core Pipeline: Netquery Text-to-SQL
- Existing LangGraph pipeline
- Modified to support SQL-only generation (no execution)
- Maintains current 6-stage processing

## API Endpoints

### `/api/generate-sql`
- **Input**: Natural language query
- **Process**: Generate SQL without execution
- **Output**:
  - `query_id`: Unique identifier
  - `sql`: Generated SQL query
- **Data Handling**: None

### `/api/execute/{query_id}`
- **Input**: Query ID from generation step
- **Process**:
  1. Smart row counting (fast check for >1000 rows vs exact count ≤1000)
  2. Execute SQL with `LIMIT 100`
  3. Cache up to 100 rows in memory
- **Output**:
  - First 30 rows for display
  - Total row count (exact if ≤1000, null if >1000)
  - `truncated` flag indicating if preview is truncated to 30 rows
- **Data Handling**:
  - Fetches max 100 rows
  - Returns max 30 rows
  - Stores up to 100 rows in cache

### `/api/interpret/{query_id}`
- **Input**: Query ID
- **Process**:
  - Use cached data (up to 100 rows)
  - Send all cached data to LLM (optimized at 100 rows)
  - Generate insights and single best visualization suggestion
- **Output**:
  - Interpretation summary and key findings
  - Single best visualization specification (or null)
  - `data_truncated` flag for frontend guidance
- **Error Handling**:
  - If LLM fails: Returns user-friendly error message with data confirmation
  - If visualization parsing fails: Returns interpretation with null visualization
- **Data Handling**:
  - Uses cached data (no re-execution)
  - All cached rows sent to LLM (exactly 100 rows or fewer)

### `/api/download/{query_id}`
- **Input**: Query ID
- **Process**:
  - Execute full SQL (no limit)
  - Stream results to CSV
- **Output**: CSV file download
- **Data Handling**:
  - Fetches ALL rows
  - Streams to avoid memory issues

## Data Flow

```
1. User enters question
   ↓
2. Generate SQL (no execution)
   ↓
3. Preview (fetch ≤100, show 30, cache data)
   ↓
4. User chooses:
   ├── Interpret (use cached ≤100 rows) → LLM → Insights + Chart Specs
   │                                              ↓
   │                                    React renders charts
   └── Download (fetch all rows) → CSV file
```

## Data Limits Summary

| Operation | Database Fetch | Memory Storage | User Sees | LLM Sees |
|-----------|---------------|----------------|-----------|----------|
| Preview | ≤100 rows | ≤100 rows | 30 rows | - |
| Interpret | 0 (uses cache) | - | text + charts | ≤100 rows |
| Download | ALL rows | 0 (streaming) | CSV file | - |

## Session Management

### Cache Structure
```python
{
    "query_id_abc123": {
        "sql": "SELECT * FROM servers WHERE...",
        "original_query": "Show me unhealthy servers",
        "data": [...up to 100 rows...],
        "total_count": 5234,
        "timestamp": "2024-01-01T10:00:00"
    }
}
```

### Cache Policy
- Store up to 100 rows per query
- Clean up after 10 minutes (configurable)
- Use in-memory dict for POC (Redis for production)

## Implementation Strategy

### Phase 1: Core Functionality
1. Modify pipeline to support `execute=False` parameter
2. Create FastAPI server with four endpoints
3. Implement simple in-memory caching
4. Basic React UI with query → preview → interpret/download flow

### Phase 2: Optimizations (Future)
- Add Redis for distributed caching
- Implement streaming for large result preview
- Add query cost estimation
- Enhanced error handling

## Technology Choices

### Why FastAPI (not Flask)
- Async support for better performance
- Built-in OpenAPI documentation
- Better type hints and validation
- Native streaming response support

### Why Direct Imports (not MCP)
- Simpler architecture
- Better performance (no IPC overhead)
- Easier debugging
- MCP only needed for external tool integration

### Why Cache Data
- Avoid re-executing SQL for interpretation
- Better user experience (faster response)
- Reduces database load

## Configuration

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///data/infrastructure.db

# Optional
CACHE_TTL=600  # seconds
MAX_CACHE_ROWS=100
PREVIEW_ROWS=30
```

## Error Handling

### Large Dataset Scenarios
- If total rows >100 and user requests interpretation:
  - Use `data_truncated` flag to inform user
  - Proceed with cached data interpretation
- Download always provides full data regardless of size

### Failed SQL Execution
- Return clear error message
- Log for debugging
- Don't cache failed queries

## Security Considerations

### For POC
- CORS configured for localhost only
- Basic error messages (no sensitive info)
- SQL injection prevented by existing validator

### For Production (Future)
- Add authentication/authorization
- Rate limiting per user
- Audit logging
- Sanitize error messages

## Visualization Integration

### Approach: LLM-Suggested Chart Configurations
The interpretation endpoint returns both textual insights and chart specifications that the frontend can render.

### Interpretation Response Structure
```json
{
  "interpretation": {
    "summary": "Analysis shows increasing failure rates in US-East region",
    "key_findings": [
      "80% of failures concentrated in one datacenter",
      "Failure rate increased 3x in the last hour"
    ],
  },
  "visualization": {
    "type": "line",
    "title": "Failure Rate Trend",
    "config": {
      "x_column": "timestamp",
      "y_column": "failure_rate",
      "reason": "Best shows the trend over time for this data"
    }
  }
}
```

### Frontend Visualization Rendering
- React receives single best chart specification (or null)
- Uses charting library (Chart.js, Recharts, or Plotly)
- Renders single interactive chart alongside interpretation
- Charts use the same cached data (≤100 rows)
- No visualization shown if LLM cannot determine appropriate chart

### Why This Approach
- **Separation of Concerns**: LLM decides what to visualize, frontend handles rendering
- **Flexibility**: Frontend can use any chart library
- **Interactivity**: Users can interact with charts (hover, zoom, filter)
- **Performance**: No image generation overhead on backend

## Frontend Data Truncation Handling

### The `data_truncated` Flag

The `/api/interpret/{query_id}` endpoint returns a `data_truncated` boolean flag to inform the frontend about data completeness for interpretation analysis.

#### Flag Logic
```python
data_truncated = total_count is None or (total_count and total_count > MAX_CACHE_ROWS)
# True if dataset > 100 cached rows
```

#### API Response Structure
```json
{
  "interpretation": { ... },
  "visualization": { ... },  // Single chart or null
  "data_truncated": true  // <- Frontend guidance flag
}
```

### Frontend Usage Scenarios

#### Scenario 1: Complete Dataset (≤100 rows)
```json
{
  "data_truncated": false
}
```
**Frontend Action**: Show interpretation without any warnings
```jsx
{!data_truncated && (
  <div className="interpretation-complete">
    <p>Analysis based on complete dataset</p>
  </div>
)}
```

#### Scenario 2: Large Dataset (>100 rows)
```json
{
  "data_truncated": true
}
```
**Frontend Action**: Show informative message about partial analysis
```jsx
{data_truncated && (
  <div className="interpretation-notice">
    <InfoIcon />
    <p>Analysis based on sample data. For complete analysis, download full dataset.</p>
    <Button onClick={downloadCSV}>Download Complete Data</Button>
  </div>
)}
```

### Recommended Frontend UX Patterns

#### 1. Visual Indicators
```jsx
<div className="interpretation-header">
  <h3>Data Insights</h3>
  {data_truncated && (
    <Badge variant="info">
      Sample Analysis
    </Badge>
  )}
</div>
```

#### 2. Contextual Help
```jsx
{data_truncated && (
  <Tooltip content="This analysis is based on a sample of your data for performance. Download the full dataset to see all records.">
    <QuestionIcon />
  </Tooltip>
)}
```

#### 3. Action Prompts
```jsx
{data_truncated && (
  <Alert type="info">
    <p>Want the complete picture?</p>
    <div className="alert-actions">
      <Button variant="primary" onClick={downloadFullData}>
        Download Full Dataset
      </Button>
      <Button variant="secondary" onClick={refineQuery}>
        Refine Query
      </Button>
    </div>
  </Alert>
)}
```

#### 4. Chart Annotations
```jsx
<Chart data={chartData}>
  {data_truncated && (
    <ChartAnnotation>
      Chart based on sample data
    </ChartAnnotation>
  )}
</Chart>
```

### Integration with Other Flags

The frontend should combine `data_truncated` with other response fields for comprehensive UX:

```jsx
const DataStatus = ({ previewResponse, interpretationResponse }) => {
  const { has_more, total_count, truncated: previewTruncated } = previewResponse;
  const { data_truncated: interpretationTruncated } = interpretationResponse;

  return (
    <div className="data-status">
      {/* Preview status */}
      {previewTruncated && (
        <p>Showing 30 of {total_count || 'many'} rows</p>
      )}

      {/* Interpretation status */}
      {interpretationTruncated && (
        <p>Analysis based on sample data for performance</p>
      )}

      {/* Action guidance */}
      {has_more && (
        <Button onClick={downloadComplete}>
          Download all {total_count || 'available'} rows
        </Button>
      )}
    </div>
  );
};
```

### Why This Approach Works

1. **Clear Separation**: Different flags for different concerns
   - `truncated`: Preview display truncation (30 of 100 rows)
   - `has_more`: Dataset size beyond cache (>100 total rows)
   - `data_truncated`: Interpretation completeness (analysis scope)

2. **User Control**: Frontend can decide how prominently to show warnings
3. **Performance Context**: Users understand why analysis is partial
4. **Action-Oriented**: Clear path to get complete data when needed
5. **Non-Intrusive**: Optional information that doesn't block workflow

## Benefits of This Architecture

1. **Simple**: No complex orchestration or MCP layers
2. **Fast**: Cached data, no re-execution
3. **Scalable**: Clear data limits prevent memory issues
4. **Flexible**: Easy to add features incrementally
5. **User-Friendly**: Quick preview, optional interpretation with visualizations
6. **Visual**: Data-driven chart suggestions enhance understanding

## What We're NOT Building (Scope Clarity)

- ❌ Multi-agent orchestration (not needed yet)
- ❌ MCP integration for React (unnecessary complexity)
- ❌ RAG system (future enhancement)
- ❌ Task decomposition (future enhancement)
- ❌ Real-time streaming updates (not required)
- ❌ Complex caching strategies (keep it simple)

## Success Criteria

- ✅ User can generate SQL from natural language
- ✅ Preview loads in <2 seconds
- ✅ Interpretation available for all datasets (with proper truncation handling)
- ✅ Visualizations suggested by LLM and rendered in React
- ✅ Full data download available for any size
- ✅ No duplicate SQL execution
- ✅ Clear feedback on data limits

## Next Steps

1. Modify netquery pipeline to add `execute=False` option
2. Create FastAPI server with four endpoints
3. Implement in-memory caching
4. Build React components for UI
5. Test with various query sizes
6. Document API for frontend team

---

