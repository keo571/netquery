"""Utilities for loading environment configuration files."""
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)


def load_environment() -> Optional[Path]:
    """Load environment variables based on SCHEMA_ID, NETQUERY_ENV, or DOTENV_PATH.

    Precedence:
    1. DOTENV_PATH environment variable (explicit override)
    2. NETQUERY_ENV or SCHEMA_ID environment variable (loads .env.<name>)
    3. Fallback to .env if present, otherwise .env.dev, then default load.

    Returns:
        Path to the dotenv file that was loaded, or None if nothing matched.
    """
    explicit_path = os.getenv("DOTENV_PATH")
    search_paths = []

    if explicit_path:
        search_paths.append(Path(explicit_path))

    # Check both NETQUERY_ENV and SCHEMA_ID for environment name
    configured_env = os.getenv("NETQUERY_ENV") or os.getenv("SCHEMA_ID")
    if configured_env:
        search_paths.append(Path(f".env.{configured_env}"))

    # Fallbacks (skip duplicates while preserving order)
    fallback_candidates = [Path(".env"), Path(".env.dev")]
    for candidate in fallback_candidates:
        if candidate not in search_paths:
            search_paths.append(candidate)

    loaded_path: Optional[Path] = None
    for path in search_paths:
        if path.exists():
            load_dotenv(dotenv_path=path)
            loaded_path = path
            LOGGER.info("Loaded environment variables from %s", path)
            break

    if loaded_path is None:
        load_dotenv()
        LOGGER.warning(
            "No explicit dotenv file found; relying on default load order."
        )

    # Determine the active environment after loading dotenv values
    env_name = os.getenv("NETQUERY_ENV")
    if not env_name and loaded_path and loaded_path.name.startswith(".env."):
        env_name = loaded_path.name.split(".env.", 1)[1]
    env_name = env_name or configured_env or "dev"

    os.environ.setdefault("NETQUERY_ENV", env_name)

    if "SCHEMA_ID" not in os.environ:
        os.environ["SCHEMA_ID"] = env_name

    if "CANONICAL_SCHEMA_PATH" not in os.environ:
        canonical_candidate = Path("schema_files") / f"{env_name}_schema.json"
        if canonical_candidate.is_file():
            os.environ["CANONICAL_SCHEMA_PATH"] = str(canonical_candidate.resolve())

    return loaded_path
