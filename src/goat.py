import time
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.timing import DetailedTimingMiddleware, TimingMiddleware

# Initialize FastMCP server
mcp = FastMCP("goat")

# Cache for field metadata (expires after 24 hours)
_FIELD_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TIMESTAMP: dict[str, float] = {}
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

# Basic timing for all requests
mcp.add_middleware(TimingMiddleware())

# Detailed per-operation timing (tools, resources, prompts)
mcp.add_middleware(DetailedTimingMiddleware())

# Caching middleware to cache responses
mcp.add_middleware(ResponseCachingMiddleware())

# Constants
GOAT_API_BASE = "https://goat.genomehubs.org/api/v2"
GOAT_DESCRIPTION = (
    "GoaT (Genomes on a Tree): a searchable datastore of "
    "genomic and sequencing project metadata"
)
USER_AGENT = "goat-app/1.0"


@mcp.resource("resource://goat/description")
async def get_goat_description() -> str:
    """Get a description of the GoaT API."""
    return GOAT_DESCRIPTION


@mcp.prompt()
async def goat_query_workflow() -> str:
    """System prompt describing the proper workflow for querying GoaT."""
    return """When answering questions about genomic data using GoaT tools:

1. ALWAYS check attribute availability first using get_attribute_selection_context
   with relevant keywords before calling get_conditional_count.

2. Extract keywords from the user's question (e.g., "assembly", "sequencing",
   "target list", "genome size") and use them to find appropriate attributes.

3. Review the returned attributes to select the most appropriate ones based on:
   - The attribute name and description
   - The display_group (e.g., assembly, genome_size, sequencing)
   - The attribute type (keyword, half_float, etc.)
   - Available enum values for keyword attributes

4. For "both X and Y" queries with keyword attributes, pass them as SEPARATE
   attribute dicts to create a logical AND. Comma-separated values create OR.

5. Only after confirming attributes exist, use get_conditional_count with the
   selected attributes.

6. Always include the GoaT web interface URL in your response for exploration."""


async def _fetch_valid_types(index: str = "taxon") -> dict[str, Any]:
    """Internal function to fetch valid attribute types from GoaT API.

    Uses in-memory cache with 24-hour TTL to avoid repeated API calls.

    Args:
        index: Index type (default: taxon)
    """
    # Check if we have a valid cached response
    current_time = time.time()
    if index in _FIELD_CACHE and index in _CACHE_TIMESTAMP:
        cache_age = current_time - _CACHE_TIMESTAMP[index]
        if cache_age < CACHE_TTL_SECONDS:
            return _FIELD_CACHE[index]

    # Cache miss or expired - fetch from API
    url = f"{GOAT_API_BASE}/resultFields?index={index}"
    data = await make_goat_request(url)
    if not data or "fields" not in data:
        return {}

    # Store in cache
    fields = data["fields"]
    _FIELD_CACHE[index] = fields
    _CACHE_TIMESTAMP[index] = current_time

    return fields


@mcp.tool()
async def get_valid_types(index: str = "taxon") -> dict[str, Any]:
    """Fetch valid attribute types from GoaT API.

    Args:
        index: Index type (default: taxon)
    """
    return await _fetch_valid_types(index)


@mcp.tool()
async def get_metadata_for_attribute(
    attribute: str, index: str = "taxon"
) -> dict[str, Any]:
    """Get metadata for a specific attribute in GoaT.

    Args:
        attribute: Name of the attribute to get metadata for
        index: Index type (default: taxon)
    """
    fields = await _fetch_valid_types(index)
    if not fields:
        return {}

    if attribute in fields:
        return fields[attribute]

    return {"error": f"Attribute '{attribute}' not found."}


async def _get_attribute_context_internal(
    keyword: str, index: str = "taxon"
) -> dict[str, Any]:
    """Internal function to get attribute selection context.

    This is called by both the resource and the tool.
    """
    fields = await _fetch_valid_types(index)
    if not fields:
        return {}

    attributes = []
    for name, field in fields.items():
        if (
            keyword.lower() in name.lower()
            or keyword.lower() in field.get("description", "").lower()
            or keyword.lower() in field.get("long_description", "").lower()
        ):
            # Include the field name with the metadata
            attr_info = {"name": name, **field}
            attributes.append(attr_info)

    return {
        "description": GOAT_DESCRIPTION,
        "attribute selection tips": (
            "Use the display_group to identify relevant categories such as "
            "assembly, genome_size and sequencing status. Choose an attribute "
            "with a matching name or description that aligns with your "
            "keyword. Consider the attribute type to distinguish between "
            "different kinds of data. Keyword attributes that have an enum "
            "can be sorted so comparison operators are valid for these "
            "attributes."
        ),
        "attributes": attributes,
    }


@mcp.tool()
async def get_attribute_selection_context(
    keyword: str, index: str = "taxon"
) -> dict[str, Any]:
    """Get context information for attribute selection.

    An LLM MUST use this to choose appropriate attributes to filter by
    based on a user query. The LLM MUST always check whether an attribute
    exists before using it in a query.

    Args:
        keyword: Keyword to guide attribute selection
        index: Index type (default: taxon)
    """
    return await _get_attribute_context_internal(keyword, index)


async def make_goat_request(url: str) -> dict[str, Any] | None:
    """Make a request to the GoaT API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def rank_description(rank: str) -> str:
    """Return a human-readable description for a given taxonomic rank."""
    return {
        "subspecies": "subspecies",
        "species": "species",
        "genus": "genera",
        "family": "families",
        "order": "orders",
        "class": "classes",
        "phylum": "phyla",
        "kingdom": "kingdoms",
        "domain": "domains",
    }.get(rank, f"{rank} level taxa")


def format_count(result: dict, taxon: str = "", rank: str = "", url: str = "") -> str:
    """Format count into a readable string with GoaT context."""
    count = result.get("count", 0)

    search_url = url.replace("/api/v2", "")
    search_url = (
        search_url.replace("count?", "search?") + "&size=10&report=sources"
    )
    return f"""
According to {GOAT_DESCRIPTION}, there are {count} {rank_description(rank)} \
within {taxon}.

This count is based on taxa with sequence data from the NCBI taxonomy,
supplemented by additional metadata from the GoaT database.

Explore these results in the GOAT web interface:
{search_url}
"""


@mcp.tool()
async def get_count(taxon: str, rank: str) -> str:
    """Get count for a GoaT query.

    An LLM can use this tool to get counts of genomes or taxa
    within a specified taxon and rank. When summarising the results, an LLM
    should include a link to the UI search page for further exploration.

    Args:
        taxon: scientific name or taxon ID of the organism
        rank: taxonomic rank to get counts for (e.g. species, genus)
    """
    url = (
        f"{GOAT_API_BASE}/count?query=tax_tree%28{taxon}%29%20AND%20"
        f"tax_rank%28{rank}%29&result=taxon&offset=0&"
        f"includeEstimates=true&taxonomy=ncbi"
    )
    data = await make_goat_request(url)

    if not data or "count" not in data:
        return "Unable to fetch count or no count found."

    return format_count(data, taxon, rank, url)


def format_attributes(attributes: list[dict]) -> str:
    """Format a list of attribute filters into a GoaT query string."""
    formatted_attrs = []
    for attr in attributes:
        name = attr.get("name")
        operator = attr.get("operator", "=")
        value = attr.get("value")

        if not name:
            continue

        if value is None:
            formatted_attrs.append(f"{name}")
            continue
        value_str = str(value)

        formatted_attrs.append(f"{name}{operator}{value_str}")

    if formatted_attrs:
        return "%20AND%20" + "%20AND%20".join(formatted_attrs)
    return ""


@mcp.tool()
async def get_conditional_count(taxon: str, rank: str, attributes: list[dict]) -> str:
    """Get count for a GoaT query with attribute filters.

    IMPORTANT: Before using this tool, you MUST first call
    get_attribute_selection_context with relevant keywords from the user's
    query to discover and validate available attributes.

    The LLM MUST use the attribute selection context tool to choose
    appropriate attributes to filter by based on the user query.
    If the query suggests filtering based on the attribute values, the LLM
    should include the 'operator' and 'value' keys in each attribute dict.
    Valid operators are '=', '!=', '>', '<', '>=', '<='. If no operator
    or value is provided, the attribute will be included without filtering.

    For keyword attributes, a list of comma separated values may be passed
    as the value, this will be treated as a logical OR. Alternatively, one
    or more values in the list may be prefixed with '!' to indicate logical
    NOT. Passing the same keyword attribute more than once with different
    values is supported and will be treated as logical AND.

    Values for any keyword with an enum should be chosen from the
    valid enum values, a list of descriptions may be available in the
    value_metadata section of the attribute metadata, which can be used to
    help match user supplied values with valid values. If the attribute has
    an enum summary, the values are sortable so comparison operators can be
    used.

    When summarizing results, the LLM MUST include the GOAT web interface
    URL provided in the response to allow users to explore the full dataset.

    Args:
        taxon: scientific name or taxon ID of the organism
        rank: taxonomic rank to get counts for (e.g. species, genus)
        attributes: list of attributes to filter by
            (e.g. assembly_level or genome_size).
            Each attribute should be a dict with 'name' and optional
            'operator' and 'value' keys.
    """
    url = (
        f"{GOAT_API_BASE}/count?query=tax_tree%28{taxon}%29%20AND%20"
        f"tax_rank%28{rank}%29{format_attributes(attributes)}&result=taxon&"
        f"offset=0&"
        f"includeEstimates=true&taxonomy=ncbi"
    )
    data = await make_goat_request(url)

    if not data or "count" not in data:
        return "Unable to fetch count or no count found."

    return format_count(data, taxon, rank, url)


@mcp.tool()
async def check_taxon_exists(name: str) -> dict:
    """Check if a specific taxon name exists in GOAT and get basic info.

    Use this to validate taxonomic names that the LLM has identified or
    translated from common names. The LLM should handle the translation
    from common names (like 'dog') to scientific names (like 'Canis').

    Args:
        name: Scientific taxon name to check (e.g. 'Canis', 'Felidae', etc.)
    """
    # Test if this taxon has any data in GOAT by doing a simple count query
    url = (
        f"{GOAT_API_BASE}/count?query=tax_tree%28{name}%29"
        f"&result=taxon&offset=0&includeEstimates=true&taxonomy=ncbi"
    )
    data = await make_goat_request(url)

    if not data or "count" not in data:
        return {
            "exists": False,
            "scientific_name": name,
            "error": "Unable to query GOAT API",
        }

    if data["count"] == 0:
        return {"exists": False, "scientific_name": name, "count_in_goat": 0}

    # Try to get more info about this taxon
    taxon_url = (
        f"{GOAT_API_BASE}/search?query=tax_name%28{name}%29"
        f"&result=taxon&size=1&taxonomy=ncbi"
    )
    taxon_data = await make_goat_request(taxon_url)

    # Extract basic info
    rank = "Unknown"
    taxon_id = ""
    if (
        taxon_data
        and "results" in taxon_data
        and taxon_data["results"]
        and "result" in taxon_data["results"][0]
    ):
        result_info = taxon_data["results"][0]["result"]
        rank = result_info.get("taxon_rank", "Unknown")
        taxon_id = str(result_info.get("taxon_id", ""))

    return {
        "exists": True,
        "scientific_name": name,
        "rank": rank,
        "taxon_id": taxon_id,
        "count_in_goat": data["count"],
    }


def main():
    # Initialize and run an HTTP server on port 8008
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8008)


if __name__ == "__main__":
    main()
