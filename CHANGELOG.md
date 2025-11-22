# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
