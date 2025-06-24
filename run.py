#!/usr/bin/env python3
"""
Netbot Multi-Agent System
Main application runner for network engineering AI assistant.
"""
import sys
import os
import logging
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Load environment variables from backend folder
load_dotenv(dotenv_path="backend/.env")

# Add backend src to path
backend_src = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Verify environment setup
def check_environment():
    """Check if environment is properly configured."""
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY not found in environment")
        print("💡 Please add GEMINI_API_KEY to your .env file")
        return False
    return True

# Import agents after path setup
try:
    from manager.graph import graph as manager_graph
    from text_to_sql.agent.graph import text_to_sql_graph
    from langchain_core.messages import HumanMessage
    print("✅ Backend agents loaded successfully")
except ImportError as e:
    print(f"❌ Error importing agents: {e}")
    print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Create Flask app
app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "frontend" / "templates"),
    static_folder=str(Path(__file__).parent / "frontend" / "static"),
)

@app.route('/')
def index():
    """Main chat interface."""
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
async def handle_query():
    """Handle user queries asynchronously."""
    data = request.get_json()
    query = data.get('query')
    include_reasoning = data.get('include_reasoning', False)
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    # The agent state needs a "messages" list with the user's query
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "run_config": {"include_reasoning": include_reasoning},
        "original_query": query,
    }
    
    try:
        # Pass the correctly structured state to the agent
        result = await manager_graph.ainvoke(initial_state)
        
        # DEBUG: Log what we actually get back
        logging.info(f"🔍 Manager graph result keys: {list(result.keys())}")
        logging.info(f"🔍 Query classification: {result.get('query_classification', 'NOT_SET')}")
        logging.info(f"🔍 Final answer exists: {'final_answer' in result}")
        if 'final_answer' in result:
            logging.info(f"🔍 Final answer preview: {result['final_answer'][:100]}...")
        
        final_response = result.get("final_answer", "Sorry, I could not process your request.")
        return jsonify({"response": final_response})
        
    except Exception as e:
        logging.error(f"Query processing error: {e}", exc_info=True)
        return jsonify({
            'error': 'An unexpected server error occurred.'
        }), 500

@app.route('/api/agents', methods=['GET'])
def get_available_agents():
    """Get list of available agents."""
    return jsonify({
        'agents': [
            {
                'id': 'manager',
                'name': 'Manager Agent',
                'description': 'Intelligently routes queries to specialized agents',
                'capabilities': ['query_classification', 'agent_routing', 'response_synthesis']
            },
            {
                'id': 'text_to_sql',
                'name': 'Text-to-SQL Agent', 
                'description': 'Converts natural language to SQL queries for infrastructure monitoring',
                'capabilities': ['sql_generation', 'database_querying', 'infrastructure_analysis']
            }
        ]
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'agents_loaded': True,
        'environment': 'ready'
    })

def main():
    """Main application entry point."""
    print("🤖 Netbot Multi-Agent System")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return
    
    # Configuration
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🌐 Server: http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"📂 Frontend: frontend/templates/")
    print(f"🧠 Backend: backend/src/")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        app.run(debug=debug, host=host, port=port)
    except KeyboardInterrupt:
        print("\n👋 Shutting down Netbot...")

if __name__ == '__main__':
    main() 