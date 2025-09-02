# Universal Text-to-SQL System

A domain-agnostic AI-powered assistant that converts natural language queries into SQL for any database. This system works automatically with any database schema through SQLAlchemy reflection and provides MCP (Model Context Protocol) server integration for AI assistants like Claude Desktop.

## Features

- **Domain-Agnostic**: Works with any database schema automatically through SQLAlchemy reflection
- **Text-to-SQL Engine**: Converts natural language to SQL for any database
- **MCP Server**: Standard Model Context Protocol server for AI assistant integration  
- **Safety Validation**: Query validation and safety checks
- **Cross-Database Support**: SQLite, PostgreSQL, MySQL, and more

## Planned Improvements

**High Priority:**
- **Query Optimizer**: Improve SQL query generation and execution efficiency  
- **Confidence Scoring**: Enhanced accuracy metrics for responses
- **Enhanced Safety**: Advanced query safety validation
- **Performance Optimization**: Better handling of large databases

**Future Considerations:**
- **Multi-modal support**: Schema diagram analysis
- **Real-time data integration**: Live database monitoring
- **Custom adapters**: Domain-specific optimizations

## Project Structure

- **src/text_to_sql/**: Domain-agnostic text-to-SQL engine
  - `models/`: Generic SQLAlchemy models using reflection
  - `tools/`: Database toolkit, schema inspector, safety validator  
  - `pipeline/`: LangGraph-based processing pipeline
  - `create_sample_data.py`: Generic sample data generator
  - `mcp_server.py`: MCP server implementation
- **tests/**: Test files for the pipeline
- **requirements.txt**: Python dependencies

## Prerequisites

- Python 3.8 or higher
- Google Gemini API key  
- Any SQL database (SQLite, PostgreSQL, MySQL, etc.)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/text-to-sql.git
   cd text-to-sql
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY and DATABASE_URL
   ```
5. Configure your database:
   ```bash
   # For SQLite (default)
   export DATABASE_URL="sqlite:///./database.db"
   
   # For PostgreSQL
   export DATABASE_URL="postgresql://user:password@localhost/dbname"
   
   # For MySQL  
   export DATABASE_URL="mysql://user:password@localhost/dbname"
   ```

## Configuration

Configure the following environment variables in `.env`:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `DATABASE_URL`: Your database connection string
- `MAX_RESULT_ROWS`: Maximum rows to return (default: 1000)

## Usage Options

### MCP Server (Primary Interface)
Use with Claude Desktop or other MCP-compatible clients:
```bash
# Run MCP server
cd src/text_to_sql
python mcp_server.py

# Or configure with Claude Desktop
```

### Testing
Run tests to verify the pipeline works:
```bash
cd tests
python test_text_to_sql_direct.py
```

## Core Engine

**Text-to-SQL Pipeline**
- Natural language query understanding  
- Automatic database schema discovery through SQLAlchemy reflection
- SQL generation using Google Gemini
- Safety validation and query execution
- Result formatting and explanation

## Database Support

The system works with any SQL database automatically:
- **SQLite**: Perfect for development and small applications
- **PostgreSQL**: Production-ready with advanced features  
- **MySQL**: Wide compatibility and performance
- **SQL Server**: Enterprise database support
- **Oracle**: Large-scale enterprise systems

## Sample Data Generation  

Generic sample data can be generated for any database schema automatically.

**How it works:**
- The `GenericSampleDataGenerator` class uses SQLAlchemy reflection to understand your schema
- Generates realistic data based on column names and types
- Handles foreign key relationships automatically
- Works with any database structure

**Manual generation:**
```bash
cd src/text_to_sql
python create_sample_data.py
```

**Configuration:**
```python
# Generate data for specific tables
create_sample_database(tables=['users', 'orders'], records_per_table=50)

# Generate for all tables  
create_sample_database(records_per_table=20)
```

## Development

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run tests:
   ```bash
   pytest
   ```
3. Format code:
   ```bash
   black .
   ```
4. Lint code:
   ```bash
   flake8
   ```

## Usage Examples

The system can answer natural language queries for any database domain:

**E-commerce Database**
- Show me the top 10 customers by total orders
- Which products have the highest revenue this month?
- Find all orders placed in the last 7 days
- What's the average order value by category?

**CRM Database**
- List all active customers with their contact information
- Show sales performance by representative
- Find customers who haven't been contacted in 30 days  
- What's the conversion rate by lead source?

**HR Database**
- Show all employees in the engineering department
- Find employees whose contracts expire this year
- What's the average salary by department?
- List all employees hired in the last 6 months

**Financial Database**
- Show monthly revenue trends
- Find all transactions above $10,000
- What's the total expenses by category?
- List all pending invoices

The system automatically discovers your schema and processes natural language queries for any database domain.

## Architecture

### Current Architecture
```
# MCP Integration (Primary)
Claude/AI Assistant → MCP Server → Text-to-SQL Pipeline → Any Database

# Direct Usage
Python Code → Text-to-SQL Pipeline → Database Results
```

### Pipeline Flow
```
Natural Language Query → Schema Analysis → SQL Generation → Safety Validation → Execution → Results
```

## Limitations

- Basic confidence scoring (improvements planned)
- No advanced query optimization yet
- Limited error recovery mechanisms
- No production-ready security features for sensitive data

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- Google Gemini (AI capabilities)  
- SQLAlchemy (database ORM and reflection)
- LangGraph (pipeline framework)
