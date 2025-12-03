"""MCP (Model Context Protocol) client for GoaT server"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for MCP streamable-http protocol"""

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or settings.mcp_server_url
        self.session_id = 0
        self.mcp_session_id: Optional[str] = None
        self.initialized = False
        self.tools: List[Dict[str, Any]] = []

    async def initialize(self):
        """Initialize connection to MCP server"""
        if self.initialized:
            return

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "public-api", "version": "1.0"},
            },
        }

        response = await self._send_request(request)
        if "error" in response:
            raise Exception(f"MCP initialization failed: {response['error']}")

        # Store session ID from response headers
        self.initialized = True

        # List available tools
        await self.list_tools()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }

        response = await self._send_request(request)
        if "error" in response:
            raise Exception(f"Failed to list tools: {response['error']}")

        self.tools = response.get("result", {}).get("tools", [])

        # Log available tools
        print(f"=== MCP server has {len(self.tools)} tools ===")
        for t in self.tools:
            print(f"  Tool: {t['name']}")

        return self.tools

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.initialized:
            await self.initialize()

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        try:
            response = await self._send_request(request)
        except Exception as e:
            # If session error, try to reinitialize once
            if "session" in str(e).lower():
                logger.info("Session error, reinitializing MCP client")
                self.initialized = False
                self.mcp_session_id = None
                await self.initialize()
                response = await self._send_request(request)
            else:
                raise

        if "error" in response:
            error_msg = response["error"]["message"]
            return {
                "content": [{"type": "text", "text": f"Error: {error_msg}"}],
                "isError": True,
            }

        return response.get("result", {})

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server via SSE"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }

            # Add session ID if we have one
            if self.mcp_session_id:
                headers["mcp-session-id"] = self.mcp_session_id

            response = await client.post(
                self.server_url,
                json=request,
                headers=headers,
            )

            # Extract session ID from response headers on first request
            if not self.mcp_session_id:
                if "mcp-session-id" in response.headers:
                    self.mcp_session_id = response.headers["mcp-session-id"]
                    logger.info(f"Got MCP session ID: {self.mcp_session_id}")

            # Parse SSE response - handle \r\n or \n line endings
            text = response.text.replace("\r\n", "\n")
            lines = text.strip().split("\n")

            logger.info(f"MCP response has {len(lines)} lines")
            for i, line in enumerate(lines):
                line = line.strip()
                logger.info(f"Line {i}: {line[:100]}")
                if line.startswith("data:"):
                    # Handle both "data: " and "data:" formats
                    data = line[5:].strip()
                    logger.info(f"Parsing JSON: {data[:100]}")
                    try:
                        result = json.loads(data)
                        logger.info("Successfully parsed JSON")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parse error: {e}")
                        continue

            logger.error(f"No valid JSON-RPC in SSE: {text[:200]}")

            # Provide specific error messages based on response
            if "No valid session ID" in text:
                raise Exception(
                    "MCP server session expired. Please try your query again."
                )
            elif "Bad Request" in text:
                raise Exception(f"MCP server error: {text[:100]}")

            raise Exception(
                "Failed to communicate with GoaT MCP server. " "Please try again."
            )

    def _next_id(self) -> int:
        """Get next request ID"""
        self.session_id += 1
        return self.session_id


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """Get or create MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        await _mcp_client.initialize()
    elif not _mcp_client.initialized:
        # Re-initialize if session was lost
        await _mcp_client.initialize()
    return _mcp_client
