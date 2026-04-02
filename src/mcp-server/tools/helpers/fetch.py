"""Constants for GenomeHubs MCP server."""

import time
from typing import Any

from ...config import API_BASE, DATASTORE_NAME
from . import constants
from .api import make_api_request

_FIELD_CACHE_TIMESTAMP: dict[str, float] = {}
_FIELD_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


async def fetch_valid_types(search_index: str = "taxon") -> dict[str, Any]:
    f"""Internal function to fetch valid attribute types from {DATASTORE_NAME} API.

    Uses in-memory cache with 24-hour TTL to avoid repeated API calls.

    Args:
        search_index: Index type (default: taxon)
    """
    global _FIELD_CACHE_TIMESTAMP
    # Check if we have a valid cached response
    current_time = time.time()
    if search_index in constants.FIELD_CACHE and search_index in _FIELD_CACHE_TIMESTAMP:
        cache_age = current_time - _FIELD_CACHE_TIMESTAMP[search_index]
        if cache_age < _FIELD_CACHE_TTL_SECONDS:
            return constants.FIELD_CACHE[search_index]

    # Cache miss or expired - fetch from API
    url = f"{API_BASE}/resultFields?result={search_index}"
    data = await make_api_request(url)
    if not data or "fields" not in data:
        return {}

    # Store in cache
    fields = data["fields"]
    constants.FIELD_CACHE[search_index] = fields
    _FIELD_CACHE_TIMESTAMP[search_index] = current_time

    return fields
