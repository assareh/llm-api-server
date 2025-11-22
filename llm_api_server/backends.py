"""Backend communication for Ollama and LM Studio."""

import time
from typing import Any, Callable, Dict, List, Tuple

import requests


def get_tool_schema(tool) -> Dict[str, Any]:
    """Extract schema from LangChain tool (handles both pydantic v1 and v2)."""
    if hasattr(tool.args_schema, "model_json_schema"):
        return tool.args_schema.model_json_schema()
    elif hasattr(tool.args_schema, "schema"):
        return tool.args_schema.schema()
    return {}


def _retry_on_connection_error(func: Callable, config, *args, **kwargs):
    """Retry a function on connection errors with exponential backoff.

    Only retries on connection errors (not on HTTP errors like 4xx/5xx).
    Uses exponential backoff with configurable attempts and initial delay.

    Args:
        func: Function to retry
        config: ServerConfig instance with retry settings
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from func

    Raises:
        Last exception if all retries fail
    """
    max_attempts = config.BACKEND_RETRY_ATTEMPTS
    initial_delay = config.BACKEND_RETRY_INITIAL_DELAY

    last_exception = None
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except requests.ConnectionError as e:
            last_exception = e
            if attempt < max_attempts - 1:  # Don't sleep on last attempt
                delay = initial_delay * (2**attempt)  # Exponential backoff: 1s, 2s, 4s
                print(f"Backend connection failed (attempt {attempt + 1}/{max_attempts}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"Backend connection failed after {max_attempts} attempts")
        except (requests.HTTPError, requests.Timeout) as e:
            # Don't retry on HTTP errors (4xx/5xx) or timeouts
            raise e

    # All retries exhausted
    raise last_exception


def call_ollama(messages: List[Dict], tools: List, config, temperature: float = 0.0, stream: bool = False):
    """Call Ollama with tool support."""
    endpoint = f"{config.OLLAMA_ENDPOINT}/api/chat"

    # Convert tools to Ollama format
    ollama_tools = []
    for tool in tools:
        schema = get_tool_schema(tool)
        tool_def = {
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": schema},
        }
        ollama_tools.append(tool_def)

    payload = {
        "model": config.BACKEND_MODEL,
        "messages": messages,
        "tools": ollama_tools,
        "stream": stream,
        "options": {"temperature": temperature},
    }

    # Set timeout as tuple (connect_timeout, read_timeout)
    timeout = (config.BACKEND_CONNECT_TIMEOUT, config.BACKEND_READ_TIMEOUT)

    # Wrap the request in retry logic
    def _make_request():
        response = requests.post(endpoint, json=payload, stream=stream, timeout=timeout)
        response.raise_for_status()
        return response

    return _retry_on_connection_error(_make_request, config)


def call_lmstudio(messages: List[Dict], tools: List, config, temperature: float = 0.0, stream: bool = False):
    """Call LM Studio with tool support."""
    endpoint = f"{config.LMSTUDIO_ENDPOINT}/chat/completions"

    # Convert tools to OpenAI format
    openai_tools = []
    for tool in tools:
        schema = get_tool_schema(tool)
        tool_def = {
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": schema},
        }
        openai_tools.append(tool_def)

    payload = {
        "model": config.BACKEND_MODEL,
        "messages": messages,
        "tools": openai_tools,
        "temperature": temperature,
        "stream": stream,
    }

    # Set timeout as tuple (connect_timeout, read_timeout)
    timeout = (config.BACKEND_CONNECT_TIMEOUT, config.BACKEND_READ_TIMEOUT)

    # Wrap the request in retry logic
    def _make_request():
        response = requests.post(endpoint, json=payload, stream=stream, timeout=timeout)
        response.raise_for_status()
        return response

    return _retry_on_connection_error(_make_request, config)


def check_ollama_health(config, timeout: int = 5) -> Tuple[bool, str]:
    """Check if Ollama backend is healthy and reachable.

    Args:
        config: ServerConfig instance
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_healthy: bool, message: str)
    """
    try:
        endpoint = f"{config.OLLAMA_ENDPOINT}/api/tags"
        response = requests.get(endpoint, timeout=timeout)
        response.raise_for_status()

        # Check if the configured model is available
        data = response.json()
        models = data.get("models", [])
        model_names = [model.get("name", "") for model in models]

        if config.BACKEND_MODEL in model_names:
            return True, f"Ollama is healthy. Model '{config.BACKEND_MODEL}' is available."
        else:
            available = ", ".join(model_names) if model_names else "none"
            return (
                False,
                f"Ollama is reachable but model '{config.BACKEND_MODEL}' not found. Available models: {available}",
            )

    except requests.Timeout:
        return False, f"Ollama health check timed out after {timeout}s. Backend may be unresponsive."
    except requests.ConnectionError:
        return False, f"Cannot connect to Ollama at {config.OLLAMA_ENDPOINT}. Is it running?"
    except Exception as e:
        return False, f"Ollama health check failed: {e!s}"


def check_lmstudio_health(config, timeout: int = 5) -> Tuple[bool, str]:
    """Check if LM Studio backend is healthy and reachable.

    Args:
        config: ServerConfig instance
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_healthy: bool, message: str)
    """
    try:
        endpoint = f"{config.LMSTUDIO_ENDPOINT}/models"
        response = requests.get(endpoint, timeout=timeout)
        response.raise_for_status()

        # LM Studio returns model list if healthy
        data = response.json()
        models = data.get("data", [])

        if models:
            model_ids = [model.get("id", "") for model in models]
            return True, f"LM Studio is healthy. {len(models)} model(s) loaded: {', '.join(model_ids)}"
        else:
            return False, "LM Studio is reachable but no models are loaded. Please load a model in LM Studio."

    except requests.Timeout:
        return False, f"LM Studio health check timed out after {timeout}s. Backend may be unresponsive."
    except requests.ConnectionError:
        return False, f"Cannot connect to LM Studio at {config.LMSTUDIO_ENDPOINT}. Is it running?"
    except Exception as e:
        return False, f"LM Studio health check failed: {e!s}"
