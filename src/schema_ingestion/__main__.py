#!/usr/bin/env python3
"""
Schema Ingestion Pipeline - Build, enrich, and manage database schemas.

This is a separate pipeline from text-to-SQL that focuses on schema metadata.

Commands:
  build     - Build canonical schema from database or Excel
  enrich    - Enrich schema with LLM-generated descriptions
  validate  - Validate schema for consistency
  diff      - Compare two schemas
  summary   - Show schema summary
"""
import argparse
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.env import load_environment

load_environment()

from src.schema_ingestion.canonical import CanonicalSchema
from src.schema_ingestion.builder import SchemaBuilder
from src.common.database.engine import get_engine
from src.common.stores.embedding_store import create_embedding_store
from src.common.embeddings import EmbeddingService

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def store_embeddings(schema: CanonicalSchema, embedding_database_url: str = None):
    """Store table embeddings in embedding store (local file or pgvector).

    Args:
        schema: Canonical schema with table descriptions
        embedding_database_url: Database URL for pgvector storage (optional)
    """
    logger.info(f"Creating embedding store...")

    # Get schema ID (namespace is embedded in schema object)
    namespace = schema.get_embedding_namespace()

    # Derive cache path from schema ID for automatic namespace isolation
    db_path = f"data/{namespace}_embeddings_cache.db"

    # Create embedding store (pgvector or local file)
    store = create_embedding_store(database_url=embedding_database_url, db_path=db_path)

    # Load embedding model
    model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    logger.info("Loading embedding model (%s)...", model_name)
    embedding_service = EmbeddingService(model_name=model_name)

    # Get namespace from schema
    namespace = schema.get_embedding_namespace()
    logger.info(f"Using namespace: {namespace}")

    # Clear existing embeddings for this namespace
    logger.info(f"Clearing existing embeddings for namespace {namespace}...")
    store.clear_namespace(namespace)

    # Generate and store embeddings for each table
    logger.info(f"Generating embeddings for {schema.total_tables} tables...")
    for table_name, table in schema.tables.items():
        # Skip tables without descriptions
        if not table.description or table.description.strip() == "":
            logger.debug(f"Skipping {table_name} (no description)")
            continue

        # Generate embedding using embed_query for consistency with query-time embeddings
        # NOTE: Using embed_query instead of embed_text ensures compatibility
        embedding = embedding_service.embed_query(table.description)

        # Store embedding
        store.store(
            table_name=table_name,
            description=table.description,
            embedding=embedding,
            namespace=namespace
        )
        logger.debug(f"Stored embedding for {table_name}")

    logger.info(f"Successfully stored embeddings for {len(schema.tables)} tables in namespace {namespace}")

    if embedding_database_url and embedding_database_url.startswith('postgresql'):
        logger.info(f"Embeddings stored in PostgreSQL pgvector: {embedding_database_url}")
    else:
        logger.info(f"Embeddings stored in SQLite: {db_path} (namespace: {namespace})")


def cmd_build(args):
    """Build canonical schema from database or Excel."""
    logger.info("=" * 60)
    logger.info("SCHEMA INGESTION PIPELINE - BUILD")
    logger.info("=" * 60)

    builder = SchemaBuilder()

    # Resolve defaults based on environment
    env_name = os.getenv("NETQUERY_ENV", "dev")

    if not args.schema_id:
        args.schema_id = os.getenv("SCHEMA_ID", env_name)

    if not args.excel:
        env_excel = os.getenv("EXCEL_SCHEMA_PATH")
        if env_excel:
            excel_path = Path(env_excel)
            if not excel_path.is_file():
                logger.warning(
                    "EXCEL_SCHEMA_PATH set to %s but file not found; falling back to database",
                    env_excel
                )
            else:
                args.excel = str(excel_path)
                logger.info("Using Excel schema from %s (NETQUERY_ENV=%s)", args.excel, env_name)

    if args.excel:
        # Build from Excel
        logger.info(f"Source: Excel ({args.excel})")
        schema = builder.build_from_excel(
            excel_path=args.excel,
            schema_id=args.schema_id,
            include_system_tables=args.include_system
        )
    else:
        # Build from database
        if args.database_url:
            os.environ['DATABASE_URL'] = args.database_url
        engine = get_engine()
        database_url = args.database_url or os.getenv('DATABASE_URL', 'default')

        logger.info(f"Source: Database ({database_url})")
        schema = builder.build_from_database(
            engine=engine,
            database_url=database_url,
            schema_id=args.schema_id,
            include_system_tables=args.include_system
        )

    # Descriptions handling
    if args.excel:
        logger.info("Using descriptions from Excel file")
    else:
        logger.info("Using table/column names as descriptions (database introspection)")

    # Save schema
    output_path = Path(args.output)
    schema.save(str(output_path))

    # Store embeddings (always enabled - required for semantic search)
    logger.info("\n" + "=" * 60)
    logger.info("STORING EMBEDDINGS")
    logger.info("=" * 60)
    store_embeddings(schema)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SCHEMA BUILD COMPLETE")
    logger.info("=" * 60)
    print(schema.summary())
    print(f"\nSchema saved to: {output_path}")

    # Validate
    errors = schema.validate()
    if errors:
        print(f"\n[WARN] Validation warnings:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nSchema validation passed")




def cmd_validate(args):
    """Validate schema for consistency."""
    logger.info("Validating schema...")

    schema = CanonicalSchema.load(args.schema)

    print("\n" + schema.summary())
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    errors = schema.validate()
    if errors:
        print(f"\n[ERROR] Found {len(errors)} validation errors:\n")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("\nSchema validation passed")


def cmd_diff(args):
    """Compare two schemas."""
    logger.info(f"Comparing schemas: {args.schema1} vs {args.schema2}")

    schema1 = CanonicalSchema.load(args.schema1)
    schema2 = CanonicalSchema.load(args.schema2)

    print("\n" + "=" * 60)
    print("SCHEMA COMPARISON")
    print("=" * 60)

    # Compare tables
    tables1 = set(schema1.tables.keys())
    tables2 = set(schema2.tables.keys())

    added = tables2 - tables1
    removed = tables1 - tables2
    common = tables1 & tables2

    print(f"\nSchema 1: {len(tables1)} tables")
    print(f"Schema 2: {len(tables2)} tables")

    if added:
        print(f"\n[+] Added tables ({len(added)}):")
        for table in sorted(added):
            print(f"  + {table}")

    if removed:
        print(f"\n[-] Removed tables ({len(removed)}):")
        for table in sorted(removed):
            print(f"  - {table}")

    # Compare common tables
    changes = []
    for table_name in common:
        t1 = schema1.tables[table_name]
        t2 = schema2.tables[table_name]

        # Compare columns
        cols1 = set(t1.columns.keys())
        cols2 = set(t2.columns.keys())

        added_cols = cols2 - cols1
        removed_cols = cols1 - cols2

        if added_cols or removed_cols:
            changes.append({
                'table': table_name,
                'added_cols': added_cols,
                'removed_cols': removed_cols
            })

    if changes:
        print(f"\n[~] Modified tables ({len(changes)}):")
        for change in changes:
            print(f"  ~ {change['table']}")
            if change['added_cols']:
                for col in sorted(change['added_cols']):
                    print(f"      + {col}")
            if change['removed_cols']:
                for col in sorted(change['removed_cols']):
                    print(f"      - {col}")

    if not added and not removed and not changes:
        print("\nSchemas are identical")


def cmd_summary(args):
    """Show schema summary."""
    schema = CanonicalSchema.load(args.schema)

    print("\n" + schema.summary())

    if args.verbose:
        print("\n" + "=" * 60)
        print("ALL TABLES")
        print("=" * 60)

        tables = sorted(schema.tables.values(), key=lambda t: t.name)
        for table in tables:
            print(f"  - {table.name} ({table.num_columns} cols, {table.num_fk_columns} FKs)")
            if args.very_verbose:
                print(f"    {table.description}")


def main():
    parser = argparse.ArgumentParser(
        description="Schema Ingestion Pipeline - Build and manage database schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build canonical schema')
    build_parser.add_argument('--database-url', help='Database URL (default: use .env)')
    build_parser.add_argument('--excel', help='Excel schema file (alternative to database)')
    build_parser.add_argument('--output', '-o', required=True, help='Output JSON file')
    build_parser.add_argument('--schema-id', default=None, help='Schema namespace ID for embedding isolation (defaults to NETQUERY_ENV)')
    build_parser.add_argument('--include-system', action='store_true', help='Include system tables')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate schema')
    validate_parser.add_argument('schema', help='Schema JSON file')

    # Diff command
    diff_parser = subparsers.add_parser('diff', help='Compare two schemas')
    diff_parser.add_argument('schema1', help='First schema JSON file')
    diff_parser.add_argument('schema2', help='Second schema JSON file')

    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show schema summary')
    summary_parser.add_argument('schema', help='Schema JSON file')
    summary_parser.add_argument('-v', '--verbose', action='store_true', help='Show all tables')
    summary_parser.add_argument('-vv', '--very-verbose', dest='very_verbose', action='store_true', help='Show full details')

    args = parser.parse_args()

    if args.command == 'build':
        cmd_build(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'diff':
        cmd_diff(args)
    elif args.command == 'summary':
        cmd_summary(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
