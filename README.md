# Netbot - Network Engineering Multi-Agent System (POC)

A proof-of-concept AI-powered assistant for network engineers, demonstrating the potential of multi-agent systems in network infrastructure management. This POC showcases intelligent agent routing and specialized capabilities for infrastructure monitoring and network procedures.

## 🚀 Current Features

- 🤖 **Manager Agent** - Basic query routing and response synthesis
- 🗃️ **Text-to-SQL Agent** - Natural language to database queries for infrastructure monitoring
- 🌐 **Web Interface** - Simple chat interface for interaction

## 🎯 Planned Improvements

### High Priority
- 📚 **Multi-shot RAG Agent** - Enhanced retrieval-augmented generation for network documentation and procedures
- 🔍 **Query Optimizer** - Improve SQL query generation and execution efficiency
- 🎯 **Confidence Scoring** - Enhanced accuracy metrics for agent responses
- **State Management** - Better handling of conversation context and history

### Future Considerations
- 🤖 **Additional Specialized Agents** - For specific network tasks
- 🔄 **Agent Collaboration** - Enhanced inter-agent communication
- 🔌 **Plugin System** - Extensible architecture for custom integrations

## 📁 Project Structure

## 🛠️ Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- SQLite database (included)

## 🚀 Quick Start

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

The application will be available at `http://localhost:5001`

## 🔧 Configuration

The following environment variables can be configured in `backend/.env`:

- `GEMINI_API_KEY`: Your Google Gemini API key
- `PORT`: Server port (default: 5001)
- `FLASK_DEBUG`: Debug mode (default: True)
- `HOST`: Server host (default: 0.0.0.0)

## 🤖 Current Agents

### Manager Agent
- Basic query routing to specialized agents
- Simple response synthesis
- Initial query classification

### Text-to-SQL Agent
- Basic natural language to SQL conversion
- Simple infrastructure monitoring
- Initial confidence scoring

## 📊 Database Schema

The POC uses SQLite with the following main tables:
- `network_devices`: Network infrastructure devices
- `interfaces`: Network interfaces
- `vlans`: VLAN configurations
- `routing_tables`: Routing information
- `monitoring_metrics`: Performance metrics

## 🗃️ Sample Data Generation

The project includes comprehensive sample data that simulates a real-world network infrastructure environment. This data is automatically generated when the application starts for the first time.

### Data Generation Process

The sample data is created by the `InfrastructureDatabaseCreator` class located in `backend/src/text_to_sql/create_sample_data.py`. This script:

1. **Creates Infrastructure Schema** - Defines 15+ tables representing a complete network infrastructure:
   - **Data Centers**: 4 global data centers (US-East, US-West, EU-Central, AP-Southeast)
   - **Network Zones**: DMZ, Internal, and Management zones per data center
   - **Load Balancers**: F5 BIG-IP, HAProxy, NGINX Plus, and Citrix ADC devices
   - **VIPs**: Virtual IP addresses for web frontend, API backend, admin portal, database, cache, and storage services
   - **VIP Members**: Backend servers with health status and performance metrics
   - **SSL Certificates**: SSL/TLS certificates with expiry monitoring
   - **Wide IP (WIP)**: Global traffic management with geographic routing
   - **Network Interfaces**: Device interface configurations
   - **Geographic Regions**: Location-based routing rules

2. **Inserts Realistic Sample Data** - Populates tables with realistic infrastructure data:
   - **4 Data Centers** across different continents
   - **8 Network Zones** with proper subnet and VLAN configurations
   - **5 Load Balancers** with different models and capabilities
   - **6 VIP Services** with health checks and SSL bindings
   - **9 Backend Servers** with varying health states and performance metrics
   - **4 SSL Certificates** with different expiry dates
   - **4 Global WIPs** with geographic routing rules
   - **7 WIP Pools** with load balancing configurations
   - **15+ Geographic Routing Rules** for global traffic distribution

3. **Creates Analytical Views** - Provides pre-built views for common monitoring queries:
   - `infrastructure_health`: Overall infrastructure health summary
   - `ssl_expiry_report`: SSL certificate expiry monitoring
   - `lb_capacity_analysis`: Load balancer capacity and performance
   - `wip_performance_overview`: Global traffic management performance
   - `wip_geographic_distribution`: Geographic traffic distribution analysis
   - `wip_health_summary`: WIP health and monitoring status

### Sample Data Characteristics

The generated data includes realistic scenarios such as:
- **Healthy and degraded services** for testing monitoring capabilities
- **SSL certificates with different expiry dates** for certificate management testing
- **Geographic routing rules** for global traffic management testing
- **Load balancer redundancy** with primary/backup configurations
- **Performance metrics** including response times and health status
- **Maintenance scenarios** for testing alerting and monitoring

### Manual Data Generation

To manually regenerate the sample data:

```bash
cd backend/src/text_to_sql
python create_sample_data.py
```

This will create a fresh database with all sample data and display statistics about the generated content.

### Data Locations

- **Primary Database**: `backend/src/data/infrastructure.db`
- **Text-to-SQL Database**: `backend/text_to_sql/infrastructure.db`
- **Generation Script**: `backend/src/text_to_sql/create_sample_data.py`

The sample data provides a comprehensive foundation for testing the Text-to-SQL agent's capabilities with realistic network infrastructure queries and monitoring scenarios.

## 🧪 Development

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

## 💬 Usage Examples

The Netbot system can handle various network engineering queries through natural language. Here are some example interactions:

### Infrastructure Monitoring
- **"Show me the status of all load balancers"**
- **"Check VIP health across all data centers"**
- **"Which SSL certificates are expiring soon?"**
- **"What's the geographic distribution of our web traffic?"**

### Performance Analysis
- **"Show load balancer capacity analysis"**
- **"Which backend servers have the highest response times?"**
- **"Give me a summary of WIP performance"**
- **"What's the health status of our global traffic management?"**

### Network Configuration
- **"List all VIPs in the DMZ zone"**
- **"Show network interfaces for lb-prod-1"**
- **"What's the current routing configuration?"**
- **"Display SSL certificate bindings"**

### System Status
- **"Give me an infrastructure health summary"**
- **"Show me data center capacity and power usage"**
- **"Which services are currently in maintenance mode?"**
- **"What's the overall system status?"**

The system automatically routes your queries to the appropriate specialized agent and provides comprehensive responses with infrastructure insights.

## ⚠️ Limitations

As a POC, this project has several limitations:
- Basic error handling and recovery
- Limited scalability
- Simple confidence scoring
- Basic state management
- Limited agent capabilities
- No production-ready security features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini for AI capabilities
- LangChain for agent framework
- Flask for web framework
