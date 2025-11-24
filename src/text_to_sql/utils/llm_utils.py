"""
Shared LLM utilities to avoid multiple model initializations.
"""
from ...api.app_context import AppContext

def get_llm():
    """Get the shared LLM instance from AppContext."""
    return AppContext.get_instance().get_llm()