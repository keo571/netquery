"""
General query handling node for Manager agent.
Responds to greetings and non-technical queries.
"""
from typing import Dict, Any
import markdown  # Import the library

from ..state import ManagerState


def handle_general_query_node(state: ManagerState) -> Dict[str, Any]:
    """
    Handles general conversation queries.
    """
    # This could be a call to another LLM or a set of canned responses.
    # For now, we use a simple, friendly response.
    response_text = (
        "Hello! I am NetBot, your network engineering assistant. "
        "I can help you with queries about your network infrastructure by "
        "querying a database, or I can answer questions from our knowledge base. "
        "How can I help you today?"
    )
    
    # ADD: Include metadata for general responses too
    run_config = state.get("run_config", {})
    include_reasoning = run_config.get("include_reasoning", False)
    
    if include_reasoning:
        metadata_html = f"""
<hr/>
<div style="font-size: 0.9em; color: #666; margin-top: 20px;">
<p><strong>Agent:</strong> Manager Agent (General Handler)</p>
<p><strong>Confidence Score:</strong> 1.00</p>
<p><strong>Query Type:</strong> General Conversation</p>
</div>
"""
        response_text += metadata_html
    
    # Convert the markdown text to HTML
    final_response_html = markdown.markdown(response_text)
    
    return {"final_answer": final_response_html} 