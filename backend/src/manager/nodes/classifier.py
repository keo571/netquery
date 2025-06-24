"""
Query classification node for Manager agent.
Classifies user queries to determine the appropriate downstream agent.
"""
import os
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import config as manager_config
from ..tools_and_schemas import RouteQuery
from ..prompts import query_classification_instructions


def classify_query_node(state: dict, config: RunnableConfig) -> Dict[str, Any]:
    """
    Classifies the user's query and adds the classification to the state.
    """
    # Initialize the LLM with the routing tool AND explicit API key
    llm = ChatGoogleGenerativeAI(
        model=manager_config.GEMINI_MODEL,
        temperature=0.0,
        max_retries=2,
        api_key=os.getenv("GEMINI_API_KEY")
    ).with_structured_output(RouteQuery)

    # Get the latest user message from the state
    latest_message = state["messages"][-1]
    user_query = latest_message.content
    
    # Format the classification prompt with the user's query
    formatted_prompt = query_classification_instructions.format(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        query=user_query
    )
    
    # Invoke the LLM to classify the query with proper instructions
    classification_result = llm.invoke(formatted_prompt, config=config)

    # Add the classification to the state with the expected key name
    return {"query_classification": classification_result.category} 