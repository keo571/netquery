"""Helpers for summarizing canonical schema information."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from src.schema_ingestion.formats.canonical import CanonicalSchema

# Simple in-memory cache keyed by absolute schema path
_SCHEMA_CACHE: Dict[Path, Dict[str, Any]] = {}


_MODULE_FILE = Path(__file__).resolve()
try:
    _REPO_ROOT = next(parent for parent in _MODULE_FILE.parents if (parent / "schema_files").exists())
except StopIteration:
    # Default to two levels up (repo root when following src/<pkg>/ layout)
    try:
        _REPO_ROOT = _MODULE_FILE.parents[2]
    except IndexError:
        _REPO_ROOT = _MODULE_FILE.parent


def _locate_path(path_like: Union[str, Path]) -> Optional[Path]:
    """Find a schema path relative to cwd or the package root."""
    candidate = Path(path_like).expanduser()
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    if candidate.exists():
        return candidate.resolve()

    repo_candidate = (_REPO_ROOT / candidate).resolve()
    return repo_candidate if repo_candidate.exists() else None


@dataclass
class TableSummary:
    name: str
    description: str
    key_columns: List[str]
    related_tables: List[str]


def _resolve_schema_path(schema_path: Optional[str] = None) -> Optional[Path]:
    """Resolve canonical schema path from explicit argument or environment."""
    if schema_path:
        return _locate_path(schema_path)

    env_path = os.getenv("CANONICAL_SCHEMA_PATH")
    if env_path:
        located = _locate_path(env_path)
        if located:
            return located

    env_name = os.getenv("NETQUERY_ENV", "dev")
    located = _locate_path(Path("schema_files") / f"{env_name}_schema.json")
    if located:
        return located

    # Last resort: allow plain schema.json if present
    located = _locate_path("schema_files/schema.json")
    if located:
        return located

    return None


def _summarize_table(table) -> TableSummary:
    columns = list(table.columns.values()) if table.columns else []
    # Prefer descriptive columns first
    key_columns: List[str] = []
    for col in columns:
        if len(key_columns) >= 4:
            break
        key_columns.append(col.name)

    related = sorted({rel.referenced_table for rel in table.relationships}) if table.relationships else []

    return TableSummary(
        name=table.name,
        description=table.description or f"Table: {table.name}",
        key_columns=key_columns,
        related_tables=related,
    )


def _generate_suggestions(tables: List[TableSummary], limit: int = 12) -> List[str]:
    """Generate lightweight example prompts for each table."""
    suggestions: List[str] = []
    for table in tables:
        human_name = table.name.replace('_', ' ')
        suggestions.append(f"Show recent {human_name} records.")
        if table.related_tables:
            suggestions.append(
                f"How do {human_name} relate to {table.related_tables[0].replace('_', ' ')}?"
            )
        if table.key_columns:
            key_col = table.key_columns[0].replace('_', ' ')
            suggestions.append(f"Summarize {human_name} by {key_col}.")
        if len(suggestions) >= limit:
            break
    return suggestions[:limit]


def get_schema_overview(schema_path: Optional[str] = None) -> Dict[str, Any]:
    """Return a cached schema overview with table summaries and suggestions."""
    env_name = os.getenv("NETQUERY_ENV", "dev")
    expected_default = str(Path("schema_files") / f"{env_name}_schema.json")

    resolved = _resolve_schema_path(schema_path)
    if not resolved:
        return {
            "schema_id": None,
            "tables": [],
            "suggested_queries": [],
            "error": {
                "message": "Canonical schema file not found",
                "environment": env_name,
                "expected_path": expected_default,
                "hint": "Run setup/ingest_schema.py build or set CANONICAL_SCHEMA_PATH to an existing schema file."
            }
        }

    resolved = resolved.resolve()
    if resolved in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[resolved]

    try:
        canonical = CanonicalSchema.load(str(resolved))
    except Exception as exc:
        return {
            "schema_id": None,
            "tables": [],
            "suggested_queries": [],
            "error": {
                "message": "Failed to load canonical schema",
                "environment": env_name,
                "resolved_path": str(resolved),
                "exception": type(exc).__name__
            }
        }

    table_summaries = [_summarize_table(table) for table in canonical.tables.values()]
    tables_payload = [
        {
            "name": summary.name,
            "description": summary.description,
            "key_columns": summary.key_columns,
            "related_tables": summary.related_tables,
        }
        for summary in table_summaries
    ]

    overview = {
        "schema_id": canonical.schema_id,
        "tables": tables_payload,
        "suggested_queries": _generate_suggestions(table_summaries),
        "source_path": str(resolved)
    }
    _SCHEMA_CACHE[resolved] = overview
    return overview
