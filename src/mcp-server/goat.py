import inspect
import os

from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.timing import DetailedTimingMiddleware, TimingMiddleware
from httpx import Request
from starlette.responses import JSONResponse

from .logging_config import get_logger
from .prompts.system import (
    get_multi_stage_prompt,
    get_parser_based_prompt,
    get_simple_search_prompt,
)
from .resources import register_resources
from .tools import register_all_tools

logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("goat")

# Register resources
register_resources(mcp)

# Register tools
register_all_tools(mcp)

# Basic timing for all requests
mcp.add_middleware(TimingMiddleware())

# Detailed per-operation timing (tools, resources, prompts)
mcp.add_middleware(DetailedTimingMiddleware())

# Caching middleware to cache responses
mcp.add_middleware(ResponseCachingMiddleware())

# Constants
GOAT_API_BASE = "https://goat.genomehubs.org/api/v2"

USER_AGENT = "goat-app/1.0"

# A/B testing: Set GOAT_PROMPT_STYLE environment variable to switch approaches
# Options: "parser" (new parsing approach) or "simple" (current simple_search approach)
PROMPT_STYLE = os.getenv("GOAT_PROMPT_STYLE", "simple")


@mcp.prompt()
async def goat_query_workflow() -> str:
    """System prompt describing the proper workflow for querying GoaT.

    The prompt style can be controlled via GOAT_PROMPT_STYLE environment variable:
    - "parser": Use parse_user_query approach (LLM extracts intent, backend processes)
    - "multi": Use multi_stage_query approach (LLM extracts, then refines)
    - "simple": Use simple_search approach (current default)
    """
    if PROMPT_STYLE == "parser":
        return get_parser_based_prompt()
    elif PROMPT_STYLE == "multi":
        return get_multi_stage_prompt()
    else:
        return get_simple_search_prompt()


async def list_registered_tools(mcp) -> list:
    tm = getattr(mcp, "_tool_manager", None)
    if tm and hasattr(tm, "get_tools"):
        try:
            maybe = tm.get_tools()
            maybe = await maybe if inspect.isawaitable(maybe) else maybe
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to get tools from tool_manager: %s", exc)
            return []

        # Normalize common shapes into a list of tool descriptors
        if maybe is None:
            return []
        if isinstance(maybe, list):
            return maybe
        if isinstance(maybe, dict):
            # MCP-style response: {"tools": [...]} -> return the list
            if "tools" in maybe and isinstance(maybe["tools"], list):
                return maybe["tools"]
            # mapping of name->info: convert to list of dicts with name
            # e.g., {"toolA": {...}, "toolB": {...}}
            try:
                return [
                    (v if isinstance(v, dict) else {"name": k, "info": v})
                    for k, v in maybe.items()
                ]
            except Exception:
                return [maybe]
        # Anything else: wrap as single-item list
        return [maybe]
    # fallback: return empty list or raise a clear error
    return []


@mcp.custom_route("/debug/tools", methods=["GET"])
async def list_tools_debug(request: Request):
    tools = await list_registered_tools(mcp)
    tool_names: list[str] = []
    for tool in tools or []:
        if isinstance(tool, str):
            tool_names.append(tool)
        elif isinstance(tool, dict):
            # common shapes: {"name": ...} or {"tool": ...}
            name = tool.get("name") or tool.get("tool") or tool.get("id")
            tool_names.append(name or str(tool))
        else:
            tool_names.append(getattr(tool, "__name__", str(tool)))

    return JSONResponse({"registered_tools": tool_names})


def main():
    # Initialize and run an HTTP server on port 8008
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8008)


if __name__ == "__main__":
    main()
