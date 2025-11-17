"""
Prompt templates for Text-to-SQL pipeline.
"""
from .result_interpretation import create_result_interpretation_prompt

__all__ = [
    'create_result_interpretation_prompt'
]