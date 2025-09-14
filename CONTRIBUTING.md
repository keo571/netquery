# Contributing to Netquery

Thank you for your interest in contributing to Netquery! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork and clone** the repository
2. **Set up development environment**:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Add your GEMINI_API_KEY to .env
   python scripts/create_sample_data.py
   ```

## Development Workflow

### Before Making Changes
1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Test current functionality**: `python gemini_cli.py "Show me all load balancers"`

### Making Changes
1. **Follow the architecture**: See `CLAUDE.md` for detailed component descriptions
2. **Test your changes**:
   ```bash
   python scripts/evaluate_queries.py --single "your test query"
   python scripts/evaluate_queries.py  # Run full evaluation
   ```

### Code Style
- **Python**: Follow PEP 8, use type hints, add docstrings
- **SQL Generation**: Always use parameterized queries, include LIMIT clauses
- **Error Handling**: Log errors with context, provide user-friendly messages
- **Safety First**: Never allow destructive operations (DELETE, DROP, UPDATE)

## Testing

### Quick Tests
```bash
# Test CLI functionality
python gemini_cli.py "Show server performance by datacenter" --html

# Test MCP server
python -m src.text_to_sql.mcp_server

# Test single query evaluation
python scripts/evaluate_queries.py --single "Show all load balancers"
```

### Comprehensive Testing
```bash
# Run full evaluation suite
python scripts/evaluate_queries.py

# Export database tables for analysis
python scripts/export_database_tables.py
```

## Pull Request Guidelines

1. **Update documentation** if you change functionality
2. **Test thoroughly** with both simple and complex queries
3. **Follow commit message format**:
   ```
   feat: add new chart type for time-series data
   fix: resolve timeout issues in database toolkit
   docs: update installation instructions
   ```

## Architecture Notes

### Key Components
- **Pipeline**: `src/text_to_sql/pipeline/` - LangGraph orchestration
- **Tools**: `src/text_to_sql/tools/` - Database operations and analysis
- **Utils**: `src/text_to_sql/utils/` - Chart generation, HTML export
- **Scripts**: Testing and data generation utilities

### Safety Requirements
- All queries must pass through safety validation
- Never expose sensitive information in logs or responses
- Always use read-only database operations
- Implement proper timeout handling

## Network Infrastructure Focus

Netquery is optimized for network infrastructure queries:

### Common Patterns
- Status queries: "Show all down load balancers"
- Performance queries: "What's the average response time by datacenter?"
- Security queries: "Which certificates expire soon?"
- Capacity queries: "Show servers above 80% utilization"

### Key Entities
- Load balancers, backend servers, VIPs
- SSL certificates and expiration tracking
- Network metrics and performance data
- Datacenter and regional organization

## Getting Help

- **Documentation**: See `README.md`, `CLAUDE.md`, and `docs/`
- **Sample Queries**: See `docs/SAMPLE_QUERIES.md`
- **Issues**: Open GitHub issues for bugs or feature requests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.