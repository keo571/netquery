# Netbot: Network Engineering Multi-Agent System (Proof of Concept)

Netbot is an AI-powered assistant for network engineers, demonstrating the potential of multi-agent systems in network infrastructure management. This proof-of-concept (POC) showcases intelligent agent routing and specialized capabilities for infrastructure monitoring and network procedures.

## Features

- Manager Agent: Query routing and response synthesis
- Text-to-SQL Agent: Natural language to database queries for infrastructure monitoring
- Web Interface: Simple chat interface for interaction

## Planned Improvements

**High Priority:**
- Multi-shot RAG Agent: Enhanced retrieval-augmented generation for network documentation and procedures
- Query Optimizer: Improve SQL query generation and execution efficiency
- Confidence Scoring: Enhanced accuracy metrics for agent responses
- State Management: Improved handling of conversation context and history

**Future Considerations:**
- Additional Specialized Agents for specific network tasks
- Agent Collaboration: Enhanced inter-agent communication
- Plugin System: Extensible architecture for custom integrations

## Project Structure

- backend/: Core backend logic, agents, and data
- frontend/: Web interface (static files and templates)
- requirements.txt: Python dependencies
- run.py: Application entry point

## Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- SQLite database (included)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/netbot.git
   cd netbot
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
   cp backend/.env.example backend/.env
   # Edit backend/.env and add your GEMINI_API_KEY
   ```
5. Run the application:
   ```bash
   python run.py
   ```
   The application will be available at http://localhost:5001

## Configuration

Configure the following environment variables in `backend/.env`:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `PORT`: Server port (default: 5001)
- `FLASK_DEBUG`: Debug mode (default: True)
- `HOST`: Server host (default: 0.0.0.0)

## Agents

**Manager Agent**
- Routes queries to specialized agents
- Synthesizes responses
- Performs initial query classification

**Text-to-SQL Agent**
- Converts natural language to SQL
- Provides infrastructure monitoring
- Performs initial confidence scoring

## Database Schema

The POC uses SQLite with the following main tables:
- `network_devices`: Network infrastructure devices
- `interfaces`: Network interfaces
- `vlans`: VLAN configurations
- `routing_tables`: Routing information
- `monitoring_metrics`: Performance metrics

## Sample Data Generation

Sample data simulating a real-world network infrastructure is automatically generated on first run.

**How it works:**
- The `InfrastructureDatabaseCreator` class (`backend/src/text_to_sql/create_sample_data.py`) creates the schema and populates tables with realistic data, including data centers, network zones, load balancers, VIPs, backend servers, SSL certificates, global traffic management, and more.
- Analytical views are created for common monitoring queries (e.g., infrastructure health, SSL expiry, load balancer capacity, WIP performance, geographic distribution).

**Manual regeneration:**
```bash
cd backend/src/text_to_sql
python create_sample_data.py
```

**Data locations:**
- Primary database: `backend/src/data/infrastructure.db`
- Text-to-SQL database: `backend/text_to_sql/infrastructure.db`
- Generation script: `backend/src/text_to_sql/create_sample_data.py`

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

Netbot can answer a variety of network engineering queries in natural language. Example queries:

**Infrastructure Monitoring**
- Show me the status of all load balancers
- Check VIP health across all data centers
- Which SSL certificates are expiring soon?
- What's the geographic distribution of our web traffic?

**Performance Analysis**
- Show load balancer capacity analysis
- Which backend servers have the highest response times?
- Give me a summary of WIP performance
- What's the health status of our global traffic management?

**Network Configuration**
- List all VIPs in the DMZ zone
- Show network interfaces for lb-prod-1
- What's the current routing configuration?
- Display SSL certificate bindings

**System Status**
- Give me an infrastructure health summary
- Show me data center capacity and power usage
- Which services are currently in maintenance mode?
- What's the overall system status?

The system automatically routes your queries to the appropriate agent and provides comprehensive infrastructure insights.

## Limitations

- Basic error handling and recovery
- Limited scalability
- Simple confidence scoring
- Basic state management
- Limited agent capabilities
- No production-ready security features

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- Google Gemini (AI capabilities)
- LangChain (agent framework)
- Flask (web framework)
