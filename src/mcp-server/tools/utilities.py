import time

from .helpers.api import make_goat_request
from .helpers.constants import GOAT_API_BASE

RANK_CACHE: list[str] = []
_RANK_CACHE_TIMESTAMP: float = 0.0
RANK_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


async def fetch_valid_ranks() -> list[str]:
    """Internal function to fetch valid taxon ranks from GoaT API.

    Uses in-memory cache with 24-hour TTL to avoid repeated API calls."""
    global RANK_CACHE, _RANK_CACHE_TIMESTAMP
    # Check if we have a valid cached response
    current_time = time.time()
    cache_age = current_time - _RANK_CACHE_TIMESTAMP
    if cache_age < RANK_CACHE_TTL_SECONDS:
        return RANK_CACHE

    # Cache miss or expired - fetch from API
    url = f"{GOAT_API_BASE}/taxonomicRanks"
    data = await make_goat_request(url)
    if not data or "ranks" not in data:
        return {}

    # Store in cache
    ranks = data["ranks"]
    RANK_CACHE = ranks
    _RANK_CACHE_TIMESTAMP = current_time

    return ranks


async def get_valid_ranks() -> list[str]:
    """Fetch valid taxon ranks from GoaT API."""
    return await fetch_valid_ranks()


async def get_example_queries(category: str = "all") -> str:
    """Get example queries to demonstrate GoaT capabilities.

    Use this tool to help users understand what kinds of questions they can ask.
    If resources are sorted then prefer the get_example_queries_resource resource.

    CRITICAL: The LLM MUST use this tool to answer requests for example queries.

    IMPORTANT: TThe LLM should present the example queries as the user would type them
    and only show the examples relevant to the requested category.

    If no category is specified, return basic examples and prompt the user that they
    can specify a category to see more examples.

    Args:
        category: Type of examples to show:
            - "all": Show all examples
            - "basic": Simple counting queries
            - "target_lists": Queries about sequencing projects
            - "assembly": Assembly quality queries
            - "taxonomy": Taxonomic and lineage queries
            - "advanced": Complex searches
    """
    examples = {
        "basic": """**Basic Counting Queries:**
- How many species are in GoaT?
- How many bat families are targeted by the VGP?
- How many cat species are missing genome size data?""",

        "target_lists": """**Target Lists and Projects:**
- Which species are on both the DToL and CANBP long lists?
- Which species are on the DToL target list?
- What are the bioprojects for bats?""",

        "assembly": """**Assembly Quality Queries:**
- Which species with chromosomal or better assemblies have over 10Mb contig N50?
- Show me a table of contig and scaffold N50 for all cat assemblies, sorted by contig N50
- How many assemblies have chromosome-level quality?""",

        "taxonomy": """**Taxonomic Queries:**
- What is the lineage for the banded snail?
- How many assemblies are there for species in the cat and dog families?
- What target lists are cats on?""",

        "advanced": """**Advanced Searches:**
- How many species have a ToLID prefix beginning with ilLys?
- How many have ToLID prefixes ending with cori?
- Which attributes support ordered keyword searches?
- Which species are on both the DToL and CANBP long lists?"""
    }

    if category == "all":
        return "\n\n".join(examples.values())

    return examples.get(category, "Unknown category. Valid categories: " + ", ".join(examples.keys()))


async def choose_search_index(query: str) -> str:
    """Choose the appropriate GoaT search index based on what is being counted/listed.

    CRITICAL: Choose the index based on what the user wants to COUNT or LIST, not what
    attributes they want to filter by.

    GoaT supports three search indices:

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
    - ✓ "Which dog family species are on DToL" → taxon (counting species)
    - ✓ "List assemblies with N50 > 1Mb" → assembly (listing assemblies)

    If uncertain, default to 'taxon' as most queries are taxonomic.

    Args:
        query: The user's full query to analyze
    """
    query_lower = query.lower()

    # Look for what is being counted/listed
    # Assembly index: explicitly counting assemblies
    assembly_patterns = [
        "how many assemblies",
        "count assemblies",
        "list assemblies",
        "which assemblies",
        "show assemblies",
        "assemblies for",
        "assemblies with",
    ]
    if any(pattern in query_lower for pattern in assembly_patterns):
        return "assembly"

    # Sample index: explicitly counting samples
    sample_patterns = [
        "how many samples",
        "count samples",
        "list samples",
        "which samples",
        "show samples",
        "samples for",
        "samples with",
    ]
    if any(pattern in query_lower for pattern in sample_patterns):
        return "sample"

    # Default to taxon for everything else (species, genera, families, etc.)
    return "taxon"


async def check_taxon_exists(name: str) -> dict:
    """Check if a specific taxon name exists in GoaT and get basic info.

    CRITICAL: Use this tool to validate scientific names before calling search_goat,
    especially when:
    - The user provides a common name that you've translated to scientific
    - You're uncertain about the correct scientific name
    - The taxon name is unfamiliar or complex
    - You want to verify the taxon exists in GoaT

    This tool handles the translation from common names to scientific names.
    You should provide the scientific name you believe is correct, and this
    tool will validate it and return a query_string for use in search_goat.

    Common name translations you should make before calling this tool:
    - "mammals" → check_taxon_exists("Mammalia")
    - "cats" → check_taxon_exists("Felidae") or check_taxon_exists("Felis")
    - "dogs" → check_taxon_exists("Canidae") or check_taxon_exists("Canis")
    - "bats" → check_taxon_exists("Chiroptera")

    The returned dict includes a query_string field, which should be used
    as the taxon parameter in subsequent GoaT search_goat calls for best results.

    Args:
        name: Scientific taxon name to check (e.g., 'Mammalia', 'Felidae', 'Canis')
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
        "query_string": f"{taxon_id}[{name}]",
        "count_in_goat": data["count"],
    }


def register_tools(mcp) -> None:
    """Register GoaT utility tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(choose_search_index)
    mcp.tool()(check_taxon_exists)
    mcp.tool()(get_example_queries)
    mcp.tool()(get_valid_ranks)
