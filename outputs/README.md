# Netquery Outputs Directory

This directory contains user-facing results from Netquery text-to-SQL queries:

## Directory Structure

- **`query_data/`** - CSV exports from text-to-SQL queries
- **`query_reports/`** - HTML reports with embedded charts and visualizations

## File Generation

Files are automatically generated when using export flags with the CLI:

```bash
python gemini_cli.py "Show network traffic trends" --csv    # Creates CSV in query_data/
python gemini_cli.py "Show server performance" --html      # Creates HTML in query_reports/
```

## Cleanup

To clean up old exports:

```bash
# Remove files older than 7 days
find outputs/query_data/ -name "*.csv" -mtime +7 -delete
find outputs/query_reports/ -name "*.html" -mtime +7 -delete
```

Or remove all exports:

```bash
rm -rf outputs/query_data/* outputs/query_reports/*
```

**Note:** This directory is gitignored as it contains generated user data.