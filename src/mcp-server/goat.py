from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.timing import DetailedTimingMiddleware, TimingMiddleware

from .logging_config import get_logger
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


@mcp.prompt()
async def goat_query_workflow() -> str:
    """System prompt describing the proper workflow for querying GoaT."""
    return """When answering questions about genomic data using GoaT tools:

═══════════════════════════════════════════════════════════════════════════════
QUICK START - For 95% of queries, use simple_search:
═══════════════════════════════════════════════════════════════════════════════

Use simple_search for straightforward questions like:
- "How many mammal species have genome size data?"
- "Which bat families are targeted by VGP?"
- "How many cat species are missing genome data?"
- "How many species have a tolid prefix beginning ilLys?"

REQUIRED: Always provide user_query (the original question)

PARAMETERS:
1. what_to_count: Choose ONE based on what's being counted:
   - "species" for "How many SPECIES..."
   - "families" for "Which FAMILIES..." or "How many FAMILIES..."
   - "genera" for "How many GENERA..."
   - "orders" for "How many ORDERS..."
   - "assemblies" for "How many ASSEMBLIES..."
   - "samples" for "How many SAMPLES..."

2. taxon: Optional scientific name for taxonomic scope
   Use these common name translations:
   - "mammals" → "Mammalia"
   - "mammals, primates, rodents" → use as-is if plural
   - "cats" → "Felis" (or "Felidae" for family)
   - "dogs" → "Canis" (or "Canidae" for family)
   - "bats" → "Chiroptera"
   - "birds" → "Aves"
   - "insects" → "Insecta"
   - "flowering plants" → "Magnoliopsida"

3. specific_attribute: Optional attribute name to filter by
   - Only use if you know the exact attribute name
   - Use get_attribute_selection_context to discover attribute names
   - When keywords relate to projects (dtol, vgp, canbp), this tool provides
     automatic disambiguation guidance to avoid confusion

EXAMPLES:
✓ simple_search(user_query="How many mammal species have genome size data?",
               what_to_count="species", taxon="Mammalia")

✓ simple_search(user_query="Which cat species are missing genome size data?",
               what_to_count="species", taxon="Felis")

✓ simple_search(user_query="How many species have tolid prefix ilLys?",
               what_to_count="species", user_query=<original query>)

═══════════════════════════════════════════════════════════════════════════════
ADVANCED - For complex queries, use search_goat:
═══════════════════════════════════════════════════════════════════════════════

Use search_goat ONLY when simple_search won't work:
- Multiple complex attribute filters
- Queries requiring AND/OR logic on attributes
- Queries with "both X and Y" or "either X or Y"
- Custom exclusion filters
- See search_goat docstring for full documentation

═══════════════════════════════════════════════════════════════════════════════
REFERENCE - Common patterns:
═══════════════════════════════════════════════════════════════════════════════

Pattern 1 - Count records in a taxon:
"How many SPECIES in MAMMALS?"
→ simple_search(what_to_count="species", taxon="Mammalia", user_query=<query>)

Pattern 2 - Count with missing/present attribute:
"How many SPECIES MISSING GENOME SIZE?"
→ simple_search(what_to_count="species", specific_attribute="genome_size", user_query=<query>)

Pattern 3 - Count in specific taxon:
"How many BAT FAMILIES?"
→ simple_search(what_to_count="families", taxon="Chiroptera", user_query=<query>)

═══════════════════════════════════════════════════════════════════════════════
FOR ADVANCED QUERIES - Use search_goat directly:
═══════════════════════════════════════════════════════════════════════════════

ALWAYS provide: user_query (critical!), search_index, and relevant filters.

Key points:
- search_index="taxon" by default (for species/families/genera/orders)
- search_index="assembly" when counting assemblies
- search_index="sample" when counting samples
- rank parameter: Include when user mentions a rank (species, family, order, etc.)
- user_query parameter: ALWAYS include the original question
- attributes: Use for complex filters; see search_goat docstring for full syntax

Complex filter examples:
- "both DToL and CANBP": [{"name": "long_list", "value": "dtol"},
                          {"name": "long_list", "value": "canbp"}]
- "either DToL or CANBP": [{"name": "long_list", "value": "dtol,canbp"}]
- "species missing genome size": [{"name": "genome_size",
                                  "exclude": ["Direct", "Descendant", "Ancestral"]}]

Report queries (histogram, scatter, sources):
1. First call search_goat to get the search_url (without report parameters)
2. Then call get_goat_report with the search_url and report_type

Always include the GoaT web interface URL in your response.

CRITICAL: If a tool call fails, show the error to the user rather than retrying."""


def main():
    # Initialize and run an HTTP server on port 8008
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8008)


if __name__ == "__main__":
    main()
