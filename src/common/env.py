"""Utilities for loading environment configuration files."""
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)


def load_environment() -> Optional[Path]:
    """Load environment variables based on SCHEMA_ID.

    Loading order:
    1. SCHEMA_ID environment variable → loads .env.<schema_id> (e.g., .env.sample)
    2. Falls back to .env if SCHEMA_ID not set

    Returns:
        Path to the dotenv file that was loaded, or None if nothing matched.
    """
    schema_id = os.getenv("SCHEMA_ID")
    loaded_path: Optional[Path] = None

    if schema_id:
        # Load .env.<schema_id> (e.g., .env.sample, .env.neila)
        env_file = Path(f".env.{schema_id}")
        if env_file.exists():
            load_dotenv(dotenv_path=env_file)
            loaded_path = env_file
            LOGGER.info("Loaded environment from %s", env_file)
        else:
            LOGGER.warning("SCHEMA_ID=%s but %s not found", schema_id, env_file)
    else:
        # Fall back to .env
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(dotenv_path=env_file)
            loaded_path = env_file
            LOGGER.info("Loaded environment from %s", env_file)
        else:
            LOGGER.warning("No .env file found and SCHEMA_ID not set")

    # Set SCHEMA_ID from loaded file if not already set
    if not schema_id and loaded_path:
        schema_id = os.getenv("SCHEMA_ID", "sample")
        os.environ.setdefault("SCHEMA_ID", schema_id)

    # Auto-detect canonical schema path if not set
    if schema_id and "CANONICAL_SCHEMA_PATH" not in os.environ:
        canonical_candidate = Path("schema_files") / f"{schema_id}_schema.json"
        if canonical_candidate.is_file():
            os.environ["CANONICAL_SCHEMA_PATH"] = str(canonical_candidate.resolve())

    return loaded_path
