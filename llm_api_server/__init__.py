"""LLM API Server - A reusable Flask server for LLM backends with tool calling."""

from .builtin_tools import (
    BUILTIN_TOOLS,
    calculate,
    create_web_search_tool,
    get_current_date,
)
from .config import ServerConfig
from .server import LLMServer

# Eval module is available but not imported by default to avoid dependency bloat
# Users can import with: from llm_api_server.eval import Evaluator, TestCase, etc.

__version__ = "0.3.0"
__all__ = [
    "BUILTIN_TOOLS",
    "LLMServer",
    "ServerConfig",
    "calculate",
    "create_web_search_tool",
    "get_current_date",
]
