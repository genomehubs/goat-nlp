"""Entry point for running the MCP server as a module.

Usage:
    python -m mcp-server
    python -m mcp_server
"""

from .goat import main

if __name__ == "__main__":
    main()
