# Repository Guidelines

## Project Structure & Module Organization
- Application code in `src/`: `api` (FastAPI server), `text_to_sql` (Gemini pipeline), `common` (database + utilities), `schema_ingestion` (reflection tooling).
- CLI entry `gemini_cli.py`; persistent data and generated exports live in `data/`, `schema_files/`, and `outputs/`.
- Support scripts sit in `setup/` for bootstrapping and environment switching; see `docs/PROFILES.md` for dev/prod setup.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` installs dependencies inside your virtualenv.
- `./setup/setup_complete.sh sqlite` (or `postgres`) provisions demo data and `.env` defaults.
- `python -m uvicorn src.api.server:app --reload --port 8000` runs the API; keep it active for integrations.
- `python gemini_cli.py "Show me all load balancers"` hits the text-to-SQL pipeline against the configured database.
- `python testing/evaluate_queries.py --single "your query"` smoke-tests a prompt; omit `--single` for the full HTML evaluation suite.
- `python testing/api_tests/test_api.py` runs request-based API checks; export the same `.env` values used by the server.

## Coding Style & Naming Conventions
- Target Python 3.8+, 4-space indentation, and type hints on public functions; mirror the docstring-first layout shown in `src/api/server.py`.
- Modules stay snake_case, classes PascalCase, async helpers descriptive verbs; prefer dependency injection over globals when touching pipeline steps.
- Use `logging` rather than bare prints and keep configuration constants grouped near the file top.

## Testing Guidelines
- Prime SQLite fixtures with `setup/create_data_sqlite.py` before running integration tests; PostgreSQL teams should mirror the schema via `setup/switch_database.sh`.
- Place new scenarios under `testing/api_tests/` using `test_<feature>.py`; reuse the Requests-based structure for consistency.
- Extend `testing/evaluate_queries.py` when altering ranking, validation, or charting logic and capture notable metrics under `outputs/`.

## Commit & Pull Request Guidelines
- Follow the existing imperative, Title-Case commit style (e.g., `Add comprehensive PostgreSQL production support`) and keep subjects under 70 characters.
- PRs should link issues, list touched modules, and attach CLI or evaluation output; call out new env flags or schema requirements.
- Verify the API smoke tests (or the relevant subset) before requesting review and document anything skipped.

## Environment & Configuration Tips
- Copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and adjust `DATABASE_URL` / `EXCEL_SCHEMA_PATH` to match the target backend.
- Use `./setup/switch_database.sh postgres` or `sqlite` to flip environments; commit hand-authored schema sources in `schema_files/` but ignore generated caches.
