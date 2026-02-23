import time

from ..config import API_BASE, DATASTORE_NAME, WEB_URL
from .helpers.api import make_api_request
from .helpers.search_index import infer_index_from_query

RANK_CACHE: list[str] = []
_RANK_CACHE_TIMESTAMP: float = 0.0
RANK_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


async def fetch_valid_ranks() -> list[str]:
    f"""Internal function to fetch valid taxon ranks from {DATASTORE_NAME} API.

    Uses in-memory cache with 24-hour TTL to avoid repeated API calls."""
    global RANK_CACHE, _RANK_CACHE_TIMESTAMP
    # Check if we have a valid cached response
    current_time = time.time()
    cache_age = current_time - _RANK_CACHE_TIMESTAMP
    if cache_age < RANK_CACHE_TTL_SECONDS:
        return RANK_CACHE

    # Cache miss or expired - fetch from API
    url = f"{API_BASE}/taxonomicRanks"
    data = await make_api_request(url)
    if not data or "ranks" not in data:
        return []

    # Store in cache
    ranks = data["ranks"]
    RANK_CACHE = ranks
    _RANK_CACHE_TIMESTAMP = current_time

    return ranks


async def get_valid_ranks() -> list[str]:
    f"""Fetch valid taxon ranks from {DATASTORE_NAME} API."""
    return await fetch_valid_ranks()


async def choose_search_index(query: str) -> dict:
    f"""Choose the appropriate {DATASTORE_NAME} search index based on what is being counted/listed.

    CRITICAL: Choose the index based on what the user wants to COUNT or LIST, not what
    attributes they want to filter by.

    {DATASTORE_NAME} supports three search indices:

    1. **taxon** (DEFAULT) - Use when counting/listing TAXONOMIC UNITS:
       - "How many species..." → taxon index
       - "Which families..." → taxon index
       - "List genera..." → taxon index
       - "How many mammal species have chromosomal assemblies" → taxon (counting species)
       - "Which cat species are missing genome data" → taxon (counting species)

    2. **assembly** - Use ONLY when counting/listing ASSEMBLIES themselves:
       - "How many assemblies..." → assembly index
       - "List all assemblies for..." → assembly index
       - "Which assemblies have contig N50 > 10Mb" → assembly (counting assemblies)
       - Note: A species can have multiple assemblies

    3. **sample** - Use ONLY when counting/listing SAMPLES themselves:
       - "How many samples..." → sample index
       - "List samples for..." → sample index
       - "Which samples have RNA-seq data" → sample (counting samples)
       - Note: A species can have many samples

    EXAMPLES:
    - ✓ "How many mammal species have assemblies" → taxon (counting species)
    - ✗ "How many mammal species have assemblies" → assembly (wrong!)
    - ✓ "How many assemblies exist for mammals" → assembly (counting assemblies)
    - ✓ "How many cat assemblies are there" → assembly (counting assemblies)
    - ✓ "Which dog family species are on DToL" → taxon (counting species)
    - ✓ "List assemblies with N50 > 1Mb" → assembly (listing assemblies)

    If uncertain, default to 'taxon' as most queries are taxonomic.

    Args:
        query: The user's full query to analyse

    Returns:
        dict with keys: search_index (one of "taxon", "assembly", "sample"), reasoning (explanation of choice)
    """
    return infer_index_from_query(query)


async def check_taxon_exists(name: str, response_format: str = "data") -> dict:
    f"""Check if a specific taxon name exists in {DATASTORE_NAME} and get basic info.

    CRITICAL: Use this tool to validate scientific names before calling submit_query,
    especially when:
    - The user provides a common name that you've translated to scientific
    - You're uncertain about the correct scientific name
    - The taxon name is unfamiliar or complex
    - You want to verify the taxon exists in {DATASTORE_NAME}

    This tool handles the translation from common names to scientific names.
    You should provide the scientific name you believe is correct, and this
    tool will validate it and return structured data for use in submit_query.

    Common name translations you should make before calling this tool:
    - "mammals" → check_taxon_exists("Mammalia")
    - "cats" → check_taxon_exists("Felidae") or check_taxon_exists("Felis")
    - "dogs" → check_taxon_exists("Canidae") or check_taxon_exists("Canis")
    - "bats" → check_taxon_exists("Chiroptera")

    The return value depends on the response_format parameter:
    - "data" (default): Returns a dict with structured data about the taxon
    - "markdown": Adds a markdown summary of the taxon information
    - "url": Adds the URL to the taxon record in {DATASTORE_NAME}
    - "full": Returns a dict with all optional information included, even if some fields are empty

    The data dict includes a query_string field, which should be used as the taxon
    parameter in subsequent {DATASTORE_NAME} process_identifiers() calls for best results.

    Args:
        name: Scientific taxon name to check
        response_format: Format preference - "data", "markdown", "url", or "full" (default: "data")

    Returns:
        dict with keys: exists, scientific_name, rank, taxon_id, query_string,
        count_in_{DATASTORE_NAME.lower()}, url, markdown
        (only populated fields depend on response_format, but full envelope always returned)
    """
    # Query API
    url = f"{API_BASE}/count?query=tax_tree%28{name}%29&result=taxon&offset=0&includeEstimates=true&taxonomy=ncbi"
    count_data = await make_api_request(url)

    if not count_data or "count" not in count_data:
        return {
            "exists": False,
            "scientific_name": name,
            "error": f"Unable to query {DATASTORE_NAME} API",
        }

    if count_data["count"] == 0:
        return {
            "exists": False,
            "scientific_name": name,
            f"count_in_{DATASTORE_NAME.lower()}": 0,
        }

    # Get detailed info
    taxon_url = f"{API_BASE}/search?query=tax_name%28{name}%29&result=taxon&size=1&taxonomy=ncbi"
    taxon_data = await make_api_request(taxon_url)

    rank = "Unknown"
    taxon_id = ""
    if taxon_data and "results" in taxon_data and taxon_data["results"]:
        result_info = taxon_data["results"][0].get("result", {})
        rank = result_info.get("taxon_rank", "Unknown")
        taxon_id = str(result_info.get("taxon_id", ""))

    record_url = f"{WEB_URL}/record?result=taxon&recordId={taxon_id}&taxonomy=ncbi"

    # Build full envelope
    result = {
        "exists": True,
        "scientific_name": name,
        "rank": rank,
        "taxon_id": taxon_id,
        "query_string": f"{taxon_id}[{name}]",
        f"count_in_{DATASTORE_NAME.lower()}": count_data["count"],
        "url": record_url,
    }

    if response_format in {"markdown", "full"}:
        # Add markdown summary
        result["markdown"] = (
            f"**{name}** ({rank})\n\n"
            f"- ID: {taxon_id}\n"
            f"- Records in {DATASTORE_NAME}: {count_data['count']}\n"
            f"- [View in {DATASTORE_NAME}]({record_url})"
        )

    # If client requested only one format, could return just that field
    # but returning full envelope is more flexible
    return result


def register_tools(mcp) -> None:
    """Register utility tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(choose_search_index)
    mcp.tool()(check_taxon_exists)
    mcp.tool()(get_valid_ranks)
    mcp.tool()(get_valid_ranks)
