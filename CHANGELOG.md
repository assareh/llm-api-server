# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-11-22

### Added
- **Web Search Tool** - Optional built-in tool for web searching
  - Dual search strategy: Ollama web search API (premium) with DuckDuckGo fallback (free)
  - `create_web_search_tool(config)` factory function
  - Requires optional `websearch` extra: `uv sync --extra websearch`
  - Uses `OLLAMA_API_KEY` from config if available
  - Graceful fallback to DuckDuckGo when API unavailable or rate-limited
  - Site filtering support (e.g., `site:hashicorp.com query`)
  - Implementation: `llm_api_server/web_search_tool.py`

- **Enhanced HTML Reports** - Beautiful markdown-formatted evaluation reports
  - Full responses with no truncation (removed 500-character limit)
  - Markdown to HTML conversion with `markdown` library
  - Collapsible long responses (>300 chars) with expand/collapse buttons
  - Syntax highlighting for code blocks
  - Professional formatting for tables, lists, and blockquotes
  - Smooth CSS transitions and modern styling
  - Requires optional `eval` extra: `uv sync --extra eval`
  - Implementation: `llm_api_server/eval/reporters.py:84-460`

- **Configuration**
  - Added `OLLAMA_API_KEY` to `ServerConfig` for web search authentication
  - Environment variable support: `OLLAMA_API_KEY` or `<PREFIX>_OLLAMA_API_KEY`

### Changed
- HTML reports now display full responses instead of truncated previews
- Code blocks in HTML reports use dark theme with syntax highlighting
- Response sections are collapsible for better readability

### Documentation
- Updated README.md with web search tool usage and eval framework features
- Updated CLAUDE.md with developer documentation for new features
- Added installation instructions for `websearch` and `eval` extras

## [0.2.0] - 2025-11-22

### Added
- **Evaluation Framework** - Comprehensive testing framework for LLM applications
  - `TestCase` class for defining test criteria with keyword validation
  - `Evaluator` class for running tests against API endpoints
  - HTML report generator with visual pass/fail results
  - JSON report generator for CI/CD integration
  - Console reporter with color-coded output
  - Custom validator support for domain-specific validation
  - Performance metrics (response time, success rate)
  - Example evaluation script (`example_evaluation.py`)
  - Complete documentation in `llm_api_server/eval/README.md`

- **Backend Configuration** (from roadmap Tier 1 & 2)
  - Backend request timeouts (`BACKEND_CONNECT_TIMEOUT`, `BACKEND_READ_TIMEOUT`)
  - Backend health checks on startup (`HEALTH_CHECK_ON_STARTUP`, `HEALTH_CHECK_TIMEOUT`)
  - Configurable host binding (`DEFAULT_HOST`) - defaults to `127.0.0.1` for security

- **Request Validation** (from roadmap Tier 1)
  - JSON request validation with 400 Bad Request responses
  - Validates `messages` field existence and format
  - Better error messages for malformed requests

### Fixed
- **Critical Fixes** (from roadmap Tier 1)
  - Backend requests now have proper timeouts (prevents infinite hangs)
  - Improved exception handling - replaced bare `except:` with specific exception types
  - Fixed WebUI subprocess pipe handling (prevents buffer-filling hangs)
  - Better error handling for backend connection failures

### Changed
- **Breaking Change**: Default host binding changed from `0.0.0.0` to `127.0.0.1` for security
  - To bind to all interfaces (allow network access), set `HOST=0.0.0.0` or `<PREFIX>_HOST=0.0.0.0`
  - Security warning displayed when binding to `0.0.0.0`

### Security
- Default localhost-only binding (`127.0.0.1`) prevents unintended network exposure
- Health checks now timeout properly instead of hanging indefinitely

## [0.1.0] - 2025-11-21

### Initial Release

Core LLM API Server package extracted from Ivan project.

**Features:**
- OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`, `/health`)
- Support for Ollama and LM Studio backends
- Tool calling with LangChain integration
- System prompt auto-reload
- Open WebUI integration
- Streaming and non-streaming responses
- Debug logging for tool execution

**Supported Backends:**
- Ollama (http://localhost:11434)
- LM Studio (http://localhost:1234/v1)
