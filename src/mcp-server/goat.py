import os

from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.timing import DetailedTimingMiddleware, TimingMiddleware

from .logging_config import get_logger
from .prompts import get_parser_based_prompt, get_simple_search_prompt
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
    - "simple": Use simple_search approach (current default)
    """
    if PROMPT_STYLE == "parser":
        return get_parser_based_prompt()
    else:
        return get_simple_search_prompt()


def main():
    # Initialize and run an HTTP server on port 8008
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8008)


if __name__ == "__main__":
    main()
