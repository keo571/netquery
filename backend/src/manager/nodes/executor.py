"""
Agent execution node for Manager agent.
Executes agents based on routing decisions.
"""
from datetime import datetime
import markdown # Import the library
import os
import logging

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Import the actual text_to_sql agent graph
from text_to_sql.agent.graph import text_to_sql_graph
from ..config import config as manager_config
from ..state import ManagerState

logger = logging.getLogger(__name__)


async def execute_single_agent_node(state: ManagerState, config: RunnableConfig) -> dict:
    """
    Executes the designated agent (Text-to-SQL or RAG) and returns the response.
    """
    agent_to_execute = state["agent_to_execute"]
    run_config = state.get("run_config", {})
    original_query = state["original_query"]

    if agent_to_execute == "text_to_sql":
        # Call the actual Text-to-SQL agent with run_config properly passed
        logger.info(f"🔍 Calling text_to_sql with query: {original_query}")
        logger.info(f"🔍 Run config: {run_config}")
        
        text_to_sql_input = {
            "original_query": original_query,
            "run_config": run_config  # This should now work since we added it to TextToSQLState
        }
        
        response = await text_to_sql_graph.ainvoke(text_to_sql_input)
        
        # DEBUG: Log what we get back from text_to_sql
        logger.info(f"🔍 Text-to-SQL response keys: {list(response.keys())}")
        logger.info(f"🔍 Has final_response: {'final_response' in response}")
        if 'final_response' in response:
            logger.info(f"🔍 Final response preview: {response['final_response'][:100]}...")
        else:
            # Check for other possible response keys
            possible_keys = ['formatted_response', 'final_answer', 'response']
            for key in possible_keys:
                if key in response:
                    logger.info(f"🔍 Found {key} instead: {response[key][:100]}...")
        
        return {"final_answer": response["final_response"]}

    elif agent_to_execute == "rag":
        # Since we don't have a real RAG agent, we simulate its response honestly.
        llm = ChatGoogleGenerativeAI(
            model=manager_config.GEMINI_MODEL,
            temperature=0.2,
            api_key=os.getenv("GEMINI_API_KEY")
        )

        # This prompt instructs the LLM to be transparent about its limitations.
        prompt = f"""
You are a helpful assistant. The user has asked a question that was routed to you, the 'knowledge base' agent.
However, **you do not currently have a knowledge base or any internal company documents to search.**

Your task is to:
1.  Clearly state that you cannot search a knowledge base because one does not exist.
2.  Based on your general training knowledge, provide a helpful, preliminary answer to the user's query.
3.  End with a strong disclaimer that this information is from general knowledge, NOT from verified company sources, and should be independently verified.

User's original query: "{original_query}"
"""
        simulated_response_text = llm.invoke(prompt, config=config).content
        final_response_html = markdown.markdown(simulated_response_text)

        return {"final_answer": final_response_html}

    else:
        # Fallback for unknown agent types
        error_response = markdown.markdown(
            "I'm sorry, I encountered an unexpected error and don't know how to handle that request. "
            "Please try rephrasing or contact support."
        )
        return {"final_answer": error_response}


def _execute_text_to_sql_agent(state: ManagerState) -> str:
    """
    Executes the text_to_sql agent and returns its final formatted response.
    """
    query = state.get("original_query", "")
    include_reasoning = state.get("include_reasoning", True)
    
    try:
        # Prepare the state for the text-to-sql agent
        sql_agent_initial_state = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "natural_language_query": query,
            "include_reasoning": include_reasoning,
            "validation_errors": []
        }

        # Invoke the text-to-sql agent graph
        result = text_to_sql_graph.invoke(sql_agent_initial_state)

        # Return the final, formatted response created by the SQL agent's interpreter
        return result.get("formatted_response", "The SQL agent did not return a response.")

    except Exception as e:
        return f"An error occurred while running the text_to_sql agent: {str(e)}"


def _simulate_rag_agent(state: ManagerState) -> str:
    """
    Simulates the RAG agent and returns a final, formatted string response.
    """
    # In a real implementation, this would call the RAG agent's graph and
    # return its 'formatted_response'. For now, we simulate a final answer.
    return """Based on general network engineering documentation, here is the standard procedure for configuring BGP:

1.  **Define BGP autonomous system (AS) number.** This is a unique identifier for your network.
2.  **Configure a router ID.** This should be a unique IP address on the router.
3.  **Define BGP neighbors and their remote AS.** These are the routers you will be peering with.
4.  **Configure network statements.** This tells BGP which networks to advertise.
5.  **Apply route maps.** Use these for fine-grained policy control.

*Note: This is a general guide. Always consult your organization's specific architecture and security policies.*
""" 