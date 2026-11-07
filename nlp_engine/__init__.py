"""
nlp_engine - NLP-based prompt analysis and optimization.

Typical use (Person 3 / FastAPI):

    from nlp_engine import analyze_prompt
    result = analyze_prompt("your prompt", "gpt-4o")      # plain dict
"""
from .analyzer import analyze_prompt, analyze_prompt_detailed, build_analysis
from .models import AnalysisResponse, Issue, PromptRequest
from .optimizer import optimize_prompt
from .tokenizer import count_tokens, register_tokenizer, tokenizer_info
from .validator import validate_optimization

__all__ = [
    "analyze_prompt", "analyze_prompt_detailed", "build_analysis", "optimize_prompt",
    "validate_optimization", "count_tokens", "tokenizer_info", "register_tokenizer",
    "PromptRequest", "AnalysisResponse", "Issue",
]
__version__ = "1.0.0"
