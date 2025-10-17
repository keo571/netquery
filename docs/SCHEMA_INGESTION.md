# Schema Ingestion Pipeline

The Schema Ingestion Pipeline is a **separate, independent system** from the text-to-SQL query pipeline. It builds, enriches, and manages database schemas in a canonical format.

## Quick Start

```bash
# Build schema (uses DATABASE_URL from .env, generates embeddings)
# Automatically extracts table/column information from database
python -m src.schema_ingestion build --output schema_files/dev_schema.json

# View schema summary
python -m src.schema_ingestion summary schema_files/dev_schema.json -v
```

## Architecture

### Package Structure

```
src/schema_ingestion/          # Schema ingestion package (independent!)
├── __main__.py               # CLI tool (run: python -m src.schema_ingestion)
├── canonical.py              # Canonical schema format
├── builder.py                # Build schema from DB/Excel
└── excel_parser.py           # Parse Excel schemas

schema_files/                  # Generated schemas
├── dev_schema.json           # Development schema output
└── prod_schema.json          # Production schema output
```

### Canonical Schema Format

All schemas are converted to a unified JSON format:

```json
{
  "schema_id": "default",
  "source_type": "database",
  "source_location": "sqlite:///data/infrastructure.db",
  "database_type": "sqlite",
  "tables": {
    "servers": {
      "name": "servers",
      "description": "Stores server infrastructure information",
      "classification": "core",
      "columns": {
        "id": {
          "name": "id",
          "data_type": "INTEGER",
          "description": "Primary key",
          "is_primary_key": true
        }
      },
      "relationships": [...]
    }
  }
}
```

**See**: [src/schema_ingestion/formats/canonical.py](../src/schema_ingestion/formats/canonical.py:14) for full schema definition.

## Pipeline Stages

### Stage 1: Build (Required)

Extracts schema from a data source and converts to canonical format.

**Sources supported:**
- SQLite databases (development)
- Excel files (production - defines relationships when DB lacks FKs)

**What it does:**
1. Introspect database/parse Excel
2. Extract foreign key relationships
3. Extract columns, types, constraints
4. Filter system tables (optional)
5. Save canonical JSON schema

**See**: [src/schema_ingestion/pipeline/builder.py](../src/schema_ingestion/pipeline/builder.py)

### Stage 2: Store Embeddings (Automatic)

Generates and stores semantic embeddings for table descriptions. **This happens automatically during build**.

**What it does:**
1. Load embedding model (sentence-transformers/all-mpnet-base-v2)
2. Generate embeddings for each table description
3. Store in local file cache (`.embeddings_cache/`)

**Storage:**
- All embeddings stored locally in `.embeddings_cache/{schema_id}/`
- JSON format with table name → embedding mappings
- Different namespaces (schema_id) keep embeddings isolated
- Example: `default` → `.embeddings_cache/default/embeddings.json`

**No database required** - embeddings are cached locally on disk.

**See**: [src/schema_ingestion/__main__.py](../src/schema_ingestion/__main__.py:34)

## Usage Scenarios

### Scenario 1: Development with SQLite

```bash
# Build schema from SQLite (uses DATABASE_URL from .env)
python -m src.schema_ingestion build --output schema_files/dev_schema.json

# View what was built
python -m src.schema_ingestion summary schema_files/dev_schema.json -v
```

**Namespace**: `default` → Embeddings in `.embeddings_cache/default/`

### Scenario 2: Production PostgreSQL (No Foreign Keys)

**Problem**: Production PostgreSQL databases often lack foreign key constraints and have cryptic table/column names.

**Solution**: Create Excel schema file with relationships AND human-readable descriptions.

```bash
# Step 1: Create Excel schema file with 2 tabs:
#
# Tab 1: 'table_schema' (required columns):
#   - table_name: Name of the table
#   - column_name: Name of the column
#   - column_type: Data type (INTEGER, VARCHAR, TIMESTAMP, etc.)
#   - table_description: Human-readable table purpose
#   - column_description: Human-readable column purpose
#
# Tab 2: 'mapping' (required columns):
#   - table_a: Source table with foreign key
#   - column_a: Foreign key column
#   - table_b: Referenced table
#   - column_b: Referenced column (usually 'id')

# Step 2: Build from Excel with prod namespace
python -m src.schema_ingestion build \
  --excel schema_files/prod_schema.xlsx \
  --output schema_files/prod_schema.json \
  --schema-id prod

# Step 3: Validate
python -m src.schema_ingestion validate schema_files/prod_schema.json
```

**Namespace**: `prod` → Embeddings in `.embeddings_cache/prod/`

**Why Excel is needed:**
- PostgreSQL has tables but no FK constraints → Excel `mapping` tab defines relationships
- Table/column names are cryptic → Excel provides human-readable descriptions
- Column types needed for SQL generation → Excel provides data types
- **Note**: No LLM enrichment needed - all information provided in Excel

### Scenario 3: Schema Updates & Comparison

```bash
# Build new schema after database changes
python -m src.schema_ingestion build --output schema_files/dev_schema_new.json

# Compare schemas to see what changed
python -m src.schema_ingestion diff schema_files/dev_schema.json schema_files/dev_schema_new.json
```

## CLI Commands Reference

### `build` - Build canonical schema

```bash
python -m src.schema_ingestion build [OPTIONS]

Options:
  --database-url TEXT       Database URL (or use .env DATABASE_URL)
  --excel TEXT             Excel schema file (alternative to database)
  --output, -o TEXT        Output JSON file (required)
  --schema-id TEXT         Schema namespace ID (default: "default")
  --include-system         Include system tables

Note: Embeddings are always generated and stored locally.
```

### `validate` - Validate schema

```bash
python -m src.schema_ingestion validate SCHEMA
```

### `diff` - Compare two schemas

```bash
python -m src.schema_ingestion diff SCHEMA1 SCHEMA2
```

### `summary` - Show schema summary

```bash
python -m src.schema_ingestion summary SCHEMA [OPTIONS]

Options:
  -v, --verbose            Show tables by classification
  -vv, --very-verbose      Show full details
```

## Environment Variables

Required for queries (not schema build):
```bash
GEMINI_API_KEY=your_api_key_here  # Required for LLM-based queries
```

Optional:
```bash
DATABASE_URL=sqlite:///data/infrastructure.db  # Default database (can be overridden with --database-url)
```

## Integration with Query System

The canonical schema is used by the text-to-SQL query pipeline:

```python
# Query pipeline loads the schema
from src.schema_ingestion.canonical import CanonicalSchema

schema = CanonicalSchema.load('schema_files/dev_schema.json')

# Use in semantic table finder
from src.text_to_sql.tools.semantic_table_finder import SemanticTableFinder

finder = SemanticTableFinder(schema)
relevant_tables = finder.find_relevant_tables("show me all servers")
```

**Workflow:**
1. **Schema Ingestion** (this pipeline) → generates `schema_files/dev_schema.json`
2. **Query Pipeline** → loads schema → processes user queries

## Excel Schema Format

For production PostgreSQL databases without foreign keys, create an Excel file with 2 tabs:

### Tab 1: `table_schema`

Required columns (all must be non-empty):

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `table_name` | TEXT | Table name from database | `orders` |
| `column_name` | TEXT | Column name from database | `customer_id` |
| `column_type` | TEXT | PostgreSQL data type | `INTEGER`, `VARCHAR`, `TIMESTAMP` |
| `table_description` | TEXT | Human-readable table purpose | `Customer orders and transactions` |
| `column_description` | TEXT | Human-readable column purpose | `Unique customer identifier` |

**Example:**

| table_name | column_name | column_type | table_description | column_description |
|-----------|-------------|-------------|-------------------|-------------------|
| orders | id | INTEGER | Customer orders and transactions | Order unique identifier |
| orders | customer_id | INTEGER | Customer orders and transactions | Customer who placed the order |
| orders | order_date | TIMESTAMP | Customer orders and transactions | When the order was placed |
| orders | total_amount | DECIMAL | Customer orders and transactions | Total order value in dollars |
| customers | id | INTEGER | Customer information | Customer unique identifier |
| customers | email | VARCHAR | Customer information | Customer email address |

### Tab 2: `mapping`

Defines foreign key relationships (4 columns):

| Column | Description | Example |
|--------|-------------|---------|
| `table_a` | Table with foreign key | `orders` |
| `column_a` | Foreign key column | `customer_id` |
| `table_b` | Referenced table | `customers` |
| `column_b` | Referenced column | `id` |

**Example:**

| table_a | column_a | table_b | column_b |
|---------|----------|---------|----------|
| orders | customer_id | customers | id |
| order_items | order_id | orders | id |
| order_items | product_id | products | id |

## Output Files

### Schema JSON (`schema_files/dev_schema.json`)

Contains full canonical schema with:
- Metadata (source, version, timestamp)
- Tables (name, description, classification)
- Columns (name, type, description, constraints)
- Relationships (foreign keys)
- Graph metrics (degree, betweenness)

### Embeddings

All embeddings are stored in local file cache with namespace isolation:

```
.embeddings_cache/
├── default/              # Development namespace
│   ├── table1.npy
│   ├── table2.npy
│   └── metadata.json
└── prod/                 # Production namespace
    ├── table1.npy
    ├── table2.npy
    └── metadata.json
```

## Best Practices

1. **Run schema ingestion before queries**
   - Schema changes require re-ingestion
   - Store schemas in version control

2. **Use different namespaces (schema-id) for dev vs prod**
   - Development: `--schema-id default` (default)
   - Production: `--schema-id prod`

3. **Validate after manual edits**
   ```bash
   python -m src.schema_ingestion validate schema_files/dev_schema.json
   ```

4. **Compare before deploying**
   ```bash
   python -m src.schema_ingestion diff schema_files/old.json schema_files/new.json
   ```

## Troubleshooting

**"psycopg2 not available" warning**
- Safe to ignore - you're using local file cache for embeddings

**Excel schema validation errors**
- Make sure Excel has both required tabs: `table_schema` and `mapping`
- Required columns in `table_schema`: `table_name`, `column_name`, `column_type`, `table_description`, `column_description`
- Required columns in `mapping`: `table_a`, `column_a`, `table_b`, `column_b`
- All fields must be non-empty (especially descriptions and column types)

**Tables missing**
- System tables excluded by default (use `--include-system`)

## Code Entry Points

| Task | File | Function/Class |
|------|------|----------------|
| CLI tool | [src/schema_ingestion/__main__.py](../src/schema_ingestion/__main__.py) | `main()` |
| Build from DB | [src/schema_ingestion/builder.py](../src/schema_ingestion/builder.py) | `SchemaBuilder.build_from_database()` |
| Build from Excel | [src/schema_ingestion/builder.py](../src/schema_ingestion/builder.py) | `SchemaBuilder.build_from_excel()` |
| Canonical format | [src/schema_ingestion/canonical.py](../src/schema_ingestion/canonical.py) | `CanonicalSchema` |
| Excel parser | [src/schema_ingestion/excel_parser.py](../src/schema_ingestion/excel_parser.py) | `ExcelSchemaParser` |

## Next Steps

After schema ingestion:
1. **Query with schema**: `python gemini_cli.py "your query" --schema schema_files/dev_schema.json`
2. **Set up MCP server**: Use schema for Claude Desktop integration
3. **Deploy to production**: Ingest production schema with `--schema-id prod`
