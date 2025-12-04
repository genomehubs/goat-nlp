"""API request utilities for GoaT MCP server."""

from typing import Any

import httpx

from ...logging_config import get_logger
from .constants import USER_AGENT

logger = get_logger(__name__)


async def make_goat_request(url: str) -> dict[str, Any] | None:
    """Make a request to the GoaT API with proper error handling."""
    logger.info(f"API Request: {url}")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            logger.info(f"API Response: HTTP {response.status_code}, {len(str(result))} bytes")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error {e.response.status_code}: {url}")
            logger.error(f"Response: {e.response.text[:500]}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout after 30s: {url}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {url}")
            logger.error(f"Error: {type(e).__name__}: {str(e)}")
            return None
