"""Query parser tool for extracting structured query components from user questions."""

from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


async def goat_query(
    user_query: str,
    taxa: list[str] | None = None,
    assemblies: list[str] | None = None,
    samples: list[str] | None = None,
    rank: str | None = None,
    attributes: list[dict[str, Any]] | None = None,
    intent: str = "count",
    taxon_filter_type: str = "children",
) -> dict[str, Any]:
    """Parse a user query into structured components for GoaT API execution.

    🔴 CRITICAL: EXTRACT AND PROVIDE the ID type from your query as a list.

    1. **taxa**: If query is about species/families/genera/orders
       - Translate common names: "mammal"→"Mammalia", "cat"→"Felis", "dog"→"Canis"
       - Each taxon name may be a prefix or partial match if the query implies it.
         Use wildcards (*) as needed.
       - Examples:
         * "How many mammal species..." → taxa=["Mammalia"]
         * "List cat families..." → taxa=["Felis"]
         * "Tell me about Canis familiaris" → taxa=["Canis familiaris"]
         * "... for humans and mice" → taxa=["Homo sapiens", "Mus musculus"]

    2. **assemblies**: If query is about genome assemblies
       - Provide assembly accession(s) (e.g., "GCF_000002305.6")
       - Examples:
         * "Details on assembly GCF_000002305.6" → assemblies=["GCF_000002305.6"]
         * "... for assemblies GCF_000002305.6 and GCA_000001405.28" →
           assemblies=["GCF_000002305.6", "GCA_000001405.28"]

    3. **samples**: If query is about DNA/RNA samples
       - Provide sample accession(s) (e.g., "SRR1234567")
       - Examples:
         * "Show sample SRR1234567" → samples=["SRR1234567"]
         * "... for samples SRR1234567 and SRR7654321" → samples=["SRR1234567", "SRR7654321"]

    📋 Extract these ADDITIONAL components:

    4. **rank**: Taxonomic rank if mentioned
       - Examples: "species", "family", "genus", "order", "class"
       - Only for taxa-based queries

    5. **attributes**: Attribute filters with modifiers/operators/values
       - Example: "genome_size < 3G" → [{"name": "genome_size", "operator": "<", "value": "3000000000"}]
       - Combined modifiers: [{"name": "genome_size", "modifier": ["min", "direct"], "operator": "<", "value": "3G"}]
       - Summary modifiers: "min", "max", "median", "length", "optional"
       - Status modifiers (converted to exclusions): "missing", "direct", "ancestral", "descendant", "estimated"

    6. **intent**: What kind of result
       - "count": Just the count ("How many...")
       - "table": List of results ("Which...", "List...")

    7. **taxon_filter_type**: Infer the type of taxon filter to apply (if taxa provided)
       - Examples:
         * "families in Felis" → "children"
         * "matching Canis*" → "matching"
         * "lineage of Mammalia", "parent taxa" → "lineage"

    Args:
        user_query: The original user question (REQUIRED)
        taxa: Scientific name(s) or taxon ID(s) for species/families/genera queries
               (e.g., ["Mammalia"], ["Felis"], ["Canis familiaris"], or NCBI ID like ["9615"])
               PROVIDE this if query mentions organism/taxon/taxa/rank!
        assemblies: Assembly accession(s) for assembly-based queries (e.g., ["GCF_000002305.6"])
                  PROVIDE this if query mentions genome assembly!
        samples: Sample accession(s) for sample-based queries (e.g., ["SRR1234567"])
                PROVIDE this if query mentions DNA/RNA sample!
        rank: Taxonomic rank for taxa queries (e.g., "species", "family", "genus")
              Only used when taxa is provided
        attributes: List of attribute filters with optional modifiers/operators/values
                   Each dict: {"name": "...", "operator": "...", "value": "...", "modifier": ...}
                   modifier can be string ("missing", "direct") or list (["min", "direct"])
        intent: Result type - "count" (default), "table", "histogram", or "record"
        taxon_filter_type: Type of taxon filter to apply if taxa provided
                           Options: "children" (default), "matching", "lineage"

    Returns:
        dict with parsed components and search result
    """
    logger.info(f"goat_query called: user_query='{user_query}', taxa={taxa}, assemblies={assemblies}, "
                f"samples={samples}, intent={intent}")

    # Determine which ID type was provided
    search_index = None

    if taxa:
        search_index = "taxon"
    elif assemblies:
        search_index = "assembly"
    elif samples:
        search_index = "sample"
    else:
        # Try to infer from query
        from .utilities import choose_search_index
        search_index = await choose_search_index(user_query)
        logger.info(f"Inferred search_index from query: {search_index}")

    # Log warnings if organism keywords found but no taxon provided
    if not taxa and search_index == "taxon":
        organism_keywords = ["mammal", "cat", "dog", "bat", "bird", "fish", "insect", "plant",
                             "primate"]
        if any(kw in user_query.lower() for kw in organism_keywords):
            logger.warning(f"⚠️ Query mentions organism but taxa not provided: '{user_query}'")
            msg = ("Did you mean to extract: 'mammal'→'Mammalia', 'cat'→'Felis', "
                   "'dog'→'Canis'?")
            logger.warning(msg)

    # Structure the parsed components
    parsed = {
        "taxa": taxa,
        "assemblies": assemblies,
        "samples": samples,
        "rank": rank,
        "attributes": attributes or [],
        "intent": intent,
        "search_index": search_index,
    }

    logger.info(f"Parsed components: {parsed}")

    # Import here to avoid circular dependency
    from .search import goat_advanced_search

    # Delegate to goat_advanced_search with the parsed components
    result = await goat_advanced_search(
        user_query=user_query,
        search_index=search_index,
        taxa=taxa,
        taxon_filter_type=taxon_filter_type,
        assemblies=assemblies,
        samples=samples,
        rank=rank,
        attributes=attributes,
        show_table=(intent == "table"),
        size=10 if intent == "table" else None,
    )

    return {
        "parsed_components": parsed,
        "user_query": user_query,
        "result": result,
    }


def register_tools(mcp) -> None:
    """Register query parser tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(goat_query)
