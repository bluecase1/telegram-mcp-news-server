# AGENTS.md

This file contains guidelines and commands for agentic coding agents working on the Telegram MCP Server project.

## Project Overview

This is a Python-based Telegram bot server implementing the Model Context Protocol (MCP) for seamless integration with language models and AI assistants. The project provides `send_message`, `send_photo`, and `send_document` tools via MCP protocol.

## Development Commands

### Environment Setup
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Telegram bot token and allowed chat IDs
```

### Running the Server
```bash
# Run MCP server (communicates via stdio)
python main.py

# The server uses stdio communication, typically used with MCP clients
# No separate dev/test modes currently configured
```

### Testing (Currently Missing - Should Be Added)
```bash
# Install test dependencies (to be added)
pip install pytest pytest-asyncio pytest-cov

# Run all tests (to be implemented)
pytest

# Run tests with coverage (to be implemented)
pytest --cov=.

# Run a single test file (to be implemented)
pytest tests/test_telegram_server.py

# Run tests matching a pattern (to be implemented)
pytest -k "test_send_message"
```

### Code Quality (Should Be Added)
```bash
# Install dev dependencies (to be added to requirements-dev.txt)
pip install black ruff isort mypy pre-commit

# Format code (to be configured)
black main.py
ruff check --fix main.py
isort main.py

# Type checking (to be configured)
mypy main.py

# Linting (to be configured)
ruff check main.py
```

## Code Style Guidelines

### General Principles
- Use Python 3.8+ with type hints
- Follow async/await patterns for all I/O operations
- Keep functions small and focused on single responsibility
- Use descriptive variable and function names
- Prefer composition over inheritance

### Import Conventions
```python
# Python standard library first
import asyncio
import os
import sys
from typing import Any, Dict, List

# External packages second
from dotenv import load_dotenv
from pydantic import BaseModel
import telegram

# Internal modules last (use relative imports for modules in same package)
from .telegram_server import TelegramMCPServer
from .config import Settings
```

### Type Definitions
```python
# Use type hints for all function parameters and return values
async def send_message(
    self, 
    chat_id: int, 
    text: str, 
    parse_mode: Optional[str] = None
) -> CallToolResult:
    pass

# Use TypedDict or Pydantic models for complex data structures
class MessageRequest(TypedDict):
    chat_id: int
    text: str
    parse_mode: Optional[str]

# Use Union for multiple possible types
Result = Union[SuccessResponse, ErrorResponse]
```

### Error Handling
```python
# Use proper exception handling with specific exception types
try:
    message = await self.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode
    )
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Message sent successfully. ID: {message.message_id}"
        )]
    )
except telegram.error.TelegramError as e:
    logger.error(f"Telegram API error: {e}")
    return CallToolResult(
        content=[TextContent(type="text", text=f"Telegram error: {str(e)}")],
        isError=True
    )
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return CallToolResult(
        content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
        isError=True
    )
```

### Naming Conventions
- **Files**: snake_case (telegram_server.py, config.py)
- **Variables**: snake_case for variables and functions
- **Constants**: UPPER_SNAKE_CASE for environment variables and constants
- **Classes**: PascalCase (TelegramMCPServer, Settings)
- **Type Aliases**: PascalCase or descriptive snake_case

### Code Organization
```
telegram-mcp-server/
├── main.py              # MCP server entry point
├── telegram_server.py   # Telegram integration logic (to be split)
├── config.py           # Configuration management (to be split)
├── tools.py            # MCP tool definitions (to be split)
├── requirements.txt     # Python dependencies
├── requirements-dev.txt # Development dependencies (to be added)
├── .env.example        # Environment variables template
├── tests/              # Test files (to be added)
│   ├── __init__.py
│   ├── test_telegram_server.py
│   └── conftest.py
├── docs/               # Documentation
└── .opencode/          # OpenCode plugin configuration
```

### Telegram Bot Specific Guidelines
```python
# Always validate chat_id against allowed list
if not await self._validate_chat_id(chat_id):
    return CallToolResult(
        content=[TextContent(type="text", text=f"Chat ID {chat_id} not allowed")],
        isError=True
    )

# Handle both URL and local file paths
if photo.startswith(('http://', 'https://')):
    message = await self.bot.send_photo(chat_id=chat_id, photo=photo)
else:
    with open(photo, 'rb') as photo_file:
        message = await self.bot.send_photo(chat_id=chat_id, photo=photo_file)

# Use proper logging
import logging
logger = logging.getLogger(__name__)
logger.info(f"Sending message to chat {chat_id}")
```

## MCP Protocol Implementation

### Server Structure
```python
# Implement MCP server interface
class MCPServer {
  async handleRequest(request: MCPRequest): Promise<MCPResponse> {
    # Handle different MCP method calls
  }
  
  async registerCapabilities(): Promise<void> {
    # Register available MCP capabilities
  }
}
```

### Testing Guidelines
- Write unit tests for all business logic
- Integration tests for Telegram bot interactions
- Mock external dependencies (Telegram API, databases)
- Test error paths and edge cases
- Use descriptive test names

### Performance Considerations
- Implement rate limiting for API calls
- Use caching for frequently accessed data
- Handle concurrent requests properly
- Monitor memory usage in long-running processes

### Security Best Practices
- Validate all input parameters
- Use environment variables for secrets
- Implement proper authentication/authorization via chat_id validation
- Log security-relevant events (but not sensitive data)
- Regular security updates for dependencies

## Configuration Management
- Use Pydantic for settings validation
- Support both .env and environment variables
- Provide sensible defaults
- Validate required settings on startup

## Future Improvements Needed
1. Add `pyproject.toml` for proper Python packaging
2. Implement comprehensive test suite with pytest
3. Add code quality tools (black, ruff, mypy)
4. Set up pre-commit hooks
5. Add CI/CD pipeline
6. Implement proper logging configuration
7. Add API rate limiting
8. Add configuration file support (JSON/YAML)