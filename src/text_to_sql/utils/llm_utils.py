"""
Shared LLM utilities to avoid multiple model initializations.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from ...common.config import config

# Global LLM instance
_llm_instance = None

def get_llm():
    """Get or create the shared LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatGoogleGenerativeAI(
            model=config.llm.model_name,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            max_retries=config.llm.max_retries,
            api_key=config.llm.effective_api_key
        )
    return _llm_instance