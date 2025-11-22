# Claude Assistant Guide - LLM API Server

Developer guide for maintaining the LLM API Server framework.

## Quick Reference

```bash
# Setup (first time)
uv sync --extra dev             # Install all dependencies + dev tools

# Before every commit
./lint.sh                       # Format and lint

# Manual linting
uv run black llm_api_server/    # Format code
uv run ruff check --fix llm_api_server/  # Lint with auto-fix

# Running commands
uv run <command>                # Run any command in the project environment
```

## Project Overview

LLM API Server is a reusable Flask framework for building OpenAI-compatible API servers with:
- LM Studio and Ollama backend support
- LangChain tool calling integration
- Open Web UI integration
- Extensible configuration system

## Linting Routine

### Standard Workflow

Always run before committing:

```bash
./lint.sh
```

This script:
1. Formats code with Black (120 char lines)
2. Lints with Ruff (auto-fixes most issues)
3. Verifies all checks pass

### Configuration

All linting settings in `pyproject.toml`:
- **Black**: 120 character lines, Python 3.8-3.12 support
- **Ruff**: Fast linter replacing flake8/isort/pylint
- **MyPy**: Optional type checking

## Development Guidelines

### Code Style
- Line length: 120 characters max
- Python version: 3.8+ compatibility
- Type hints: Use modern syntax where possible
- Imports: Auto-sorted by Ruff (stdlib → third-party → first-party)

### Package Structure

```
llm-api-server/
├── llm_api_server/
│   ├── __init__.py         # Package exports
│   ├── server.py           # Core LLMServer class
│   ├── backends.py         # Backend integrations
│   ├── config.py           # ServerConfig base class
│   ├── builtin_tools.py    # Built-in tools (date, calculate, web search)
│   ├── web_search_tool.py  # Web search implementation (Ollama + DuckDuckGo)
│   └── webui.py            # Open Web UI integration
├── setup.py                # Package installation
├── pyproject.toml          # Packaging & linting config
└── README.md               # Package documentation
```

### Making Changes

1. **Core server** (`server.py`): Flask app, routing, tool calling loop
2. **Backends** (`backends.py`): Ollama/LM Studio communication
3. **Config** (`config.py`): Configuration and environment loading
4. **Built-in tools** (`builtin_tools.py`): Common tools (date, calculate, web search factory)
5. **Web search** (`web_search_tool.py`): Ollama API + DuckDuckGo fallback implementation
6. **Web UI** (`webui.py`): Open Web UI subprocess management

### Adding Features

When adding new features, consider:
- **Backwards compatibility**: This is used by multiple projects
- **Configuration options**: Make features configurable
- **Documentation**: Update README.md and docstrings
- **Examples**: Update consuming projects (Ivan, milesoss)

## Testing

Since this is a framework library:

1. **Local testing**: Install in consuming project
   ```bash
   cd ../milesoss  # or ../Ivan
   uv sync  # Will pull llm-api-server from GitHub
   uv run python milesoss.py --no-webui
   ```

2. **Integration testing**: Verify in both Ivan and milesoss

3. **API testing**: Test OpenAI-compatible endpoints
   ```bash
   curl http://localhost:8000/v1/models
   curl http://localhost:8000/health
   ```

## Installation Options

```bash
# Using uv (recommended)
uv sync                   # Install core dependencies
uv sync --extra dev       # With development tools
uv sync --extra webui     # With Open Web UI
uv sync --extra websearch # With web search tool
uv sync --extra eval      # With HTML report markdown formatting
uv sync --all-extras      # Everything

# Using pip (legacy)
pip install -e .
pip install -e '.[dev]'
pip install -e '.[webui]'
```

## Git Workflow

Standard GitHub workflow:

```bash
# Make changes
./lint.sh  # Format and lint

# Commit
git add .
git commit -m "feat: description

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to GitHub
git push
```

Changes are now distributed via GitHub. Consuming projects install with:
```
llm-api-server @ git+https://github.com/assareh/llm-api-server.git
```

## Key Components

### LLMServer Class
Main server class that consuming projects instantiate:
```python
server = LLMServer(
    name="MyApp",
    model_name="myapp/model",
    tools=ALL_TOOLS,
    config=config,
    default_system_prompt="You are...",
    init_hook=initialization_function,
    logger_names=["myapp.tools"]
)
```

### ServerConfig Base Class
Extensible configuration loaded from environment:
```python
class MyConfig(ServerConfig):
    CUSTOM_SETTING: str = "default"

config = ServerConfig.from_env("MYAPP_")
```

### Backend Support
- **Ollama**: Native Ollama API format
- **LM Studio**: OpenAI-compatible format
- **Tool calling**: Automatic conversion and execution

### Built-in Tools

The framework provides reusable tools:

**Always available:**
- `get_current_date()` - Returns current date in YYYY-MM-DD format
- `calculate(expression)` - Safe mathematical expression evaluator

**Optional (requires `--extra websearch`):**
- `create_web_search_tool(config)` - Web search with dual strategy:
  - Tries Ollama web search API if `OLLAMA_API_KEY` is configured
  - Falls back to DuckDuckGo search (free, rate-limited)
  - Supports site filtering: `site:hashicorp.com query`
  - Implementation: `llm_api_server/web_search_tool.py`

**Usage:**
```python
from llm_api_server import BUILTIN_TOOLS, create_web_search_tool

# With web search
web_search = create_web_search_tool(config)
tools = BUILTIN_TOOLS + [web_search]
```

### Evaluation Framework

The framework includes a comprehensive evaluation system in `llm_api_server/eval/`:

**Components:**
- `Evaluator` - Runs test cases against LLM API
- `TestCase` - Defines questions and validation rules
- `TestResult` - Contains test outcomes and metrics
- `HTMLReporter` - Generates beautiful HTML reports with markdown formatting
- `JSONReporter` - Machine-readable JSON output
- `ConsoleReporter` - Terminal-friendly output

**HTML Report Features (requires `--extra eval`):**
- **Markdown to HTML conversion** using `markdown` library
- **Full responses** - No truncation, all content visible
- **Collapsible sections** - Long responses start collapsed with expand/collapse buttons
- **Syntax highlighting** - Code blocks, tables, lists, blockquotes
- **Professional styling** - Dark code blocks, formatted tables, styled blockquotes
- Implementation: `llm_api_server/eval/reporters.py:84-460`

**Key files:**
- `evaluator.py` - Test execution engine
- `test_case.py` - Data models for tests and results
- `reporters.py` - HTML/JSON/Console report generation
- `validators.py` - Response validation logic

See `llm_api_server/eval/README.md` for complete documentation.

## Consuming Projects

Current projects using this framework:
- **Ivan**: HashiCorp documentation assistant
- **milesoss**: Credit card rewards optimizer

When making changes, test in both projects.

## Resources

- [README.md](README.md) - Package documentation
- [Black Docs](https://black.readthedocs.io/)
- [Ruff Docs](https://docs.astral.sh/ruff/)
- [Flask](https://flask.palletsprojects.com/)
- [LangChain](https://python.langchain.com/)

---

*Last updated: 2025-11-22*
*Version: 0.1.0*
