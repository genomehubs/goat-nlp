import inspect
import os
from pathlib import Path
from typing import Any, Dict

from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.timing import DetailedTimingMiddleware, TimingMiddleware
from httpx import Request
from jinja2 import Template
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, HTMLResponse, JSONResponse

try:
    from .config import BROWSER_PAGE_CONFIG, LOGO_FILE
except ImportError:
    # Fallback to example config if custom config is not provided
    from .config_example import BROWSER_PAGE_CONFIG, LOGO_FILE

from .logging_config import get_logger
from .prompts.system import (
    get_multi_stage_prompt,
    get_parser_based_prompt,
    get_simple_search_prompt,
)
from .tools import register_all_tools

logger = get_logger(__name__)

# Load browser page template
_BROWSER_PAGE_TEMPLATE = None


def get_browser_page_template() -> Template:
    """Load and cache the browser page template."""
    global _BROWSER_PAGE_TEMPLATE
    if _BROWSER_PAGE_TEMPLATE is None:
        html_file = Path(__file__).parent / "browser_page.html"
        template_str = html_file.read_text(encoding="utf-8")
        _BROWSER_PAGE_TEMPLATE = Template(template_str)
    return _BROWSER_PAGE_TEMPLATE


def render_browser_page(config: Dict[str, Any] = None) -> str:
    """Render the browser page with custom configuration."""
    template = get_browser_page_template()
    config = config or BROWSER_PAGE_CONFIG
    # Add logo_path derived from logo filename
    render_config = {**config, "logo_path": "/site_logo.png"}
    return template.render(**render_config)


# Middleware to serve HTML for browser GET requests to /mcp
class BrowserFriendlyMCPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only intercept GET requests to /mcp
        if request.method == "GET" and request.url.path == "/mcp":
            accept_header = request.headers.get("accept", "").lower()
            user_agent = request.headers.get("user-agent", "").lower()

            # Check if this is a browser
            is_browser = (
                "text/html" in accept_header or
                ("text/event-stream" not in accept_header and
                 any(ua in user_agent for ua in ["mozilla", "chrome", "safari", "edge", "opera"]))
            )

            if is_browser:
                return HTMLResponse(render_browser_page())

        # For everything else, continue to next middleware/handler
        return await call_next(request)


# Initialize FastMCP server
mcp = FastMCP("goat")

# Register tools
register_all_tools(mcp)

# Basic timing for all requests
mcp.add_middleware(TimingMiddleware())

# Detailed per-operation timing (tools, resources, prompts)
mcp.add_middleware(DetailedTimingMiddleware())

# Caching middleware to cache responses
mcp.add_middleware(ResponseCachingMiddleware())

# NOTE: Browser-friendly middleware is added in main() by wrapping the ASGI app

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


@mcp.custom_route("/site_logo.png", methods=["GET"])
async def serve_logo(request: Request):
    """Serve the site logo image."""
    logo_path = Path(__file__).parent / LOGO_FILE
    if logo_path.exists():
        return FileResponse(logo_path, media_type="image/png")
    else:
        return JSONResponse({"error": "Logo not found"}, status_code=404)


def main():
    # Get the underlying Starlette app and add our middleware directly
    # This ensures it runs before FastMCP's internal routing
    app = mcp.http_app(transport="streamable-http")

    # Wrap the app with our browser-friendly middleware
    wrapped_app = BrowserFriendlyMCPMiddleware(app)

    # Run the wrapped app
    import uvicorn
    uvicorn.run(wrapped_app, host="127.0.0.1", port=8008)


if __name__ == "__main__":
    main()
    main()
    main()
