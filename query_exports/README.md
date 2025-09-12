# Query Exports Directory

This directory contains exported query results in various formats:

- `.csv` - Raw data exports
- `.html` - Formatted reports with visualizations
- `.pdf` - Formatted reports for sharing

Files are automatically generated when using `--csv`, `--html`, or `--pdf` flags with the CLI.

## Cleanup

To clean up old exports:

```bash
# Remove files older than 7 days
find query_exports/ -name "query_*.csv" -mtime +7 -delete
find query_exports/ -name "query_*.html" -mtime +7 -delete
find query_exports/ -name "query_*.pdf" -mtime +7 -delete
```

Or remove all exports:

```bash
rm query_exports/query_*
```