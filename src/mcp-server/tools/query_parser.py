"""Query parser tool for extracting structured query components from user questions."""

from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


async def goat_query(
    user_query: str,
    taxon: str | None = None,
    assembly: str | None = None,
    sample: str | None = None,
    rank: str | None = None,
    attributes: list[dict[str, Any]] | None = None,
    intent: str = "count",
) -> dict[str, Any]:
    """Parse a user query into structured components for GoaT API execution.

    🔴 CRITICAL: EXTRACT AND PROVIDE the ID type from your query:

    1. **taxon**: If query is about species/families/genera/orders
       - Translate common names: "mammal"→"Mammalia", "cat"→"Felis", "dog"→"Canis"
       - Examples:
         * "How many mammal species..." → taxon="Mammalia"
         * "List cat families..." → taxon="Felis"
         * "Tell me about Canis familiaris" → taxon="Canis familiaris"

    2. **assembly**: If query is about genome assemblies
       - Provide assembly accession (e.g., "GCF_000002305.6")
       - Example: "Details on assembly GCF_000002305.6" → assembly="GCF_000002305.6"

    3. **sample**: If query is about DNA/RNA samples
       - Provide sample accession (e.g., "SRR1234567")
       - Example: "Show sample SRR1234567" → sample="SRR1234567"

    📋 Extract these ADDITIONAL components:

    4. **rank**: Taxonomic rank if mentioned
       - Examples: "species", "family", "genus", "order", "class"
       - Only for taxon-based queries

    5. **attributes**: Attribute filters with modifiers/operators/values
       - Example: "genome_size < 3G" → [{"name": "genome_size", "operator": "<", "value": "3000000000"}]
       - Combined modifiers: [{"name": "genome_size", "modifier": ["min", "direct"], "operator": "<", "value": "3G"}]

    6. **intent**: What kind of result
       - "count": Just the count ("How many...")
       - "table": List of results ("Which...", "List...")
       - "histogram": Distribution ("Show distribution...")
       - "record": Single record details ("Tell me about...")

    Args:
        user_query: The original user question (REQUIRED)
        taxon: Scientific name or taxon ID for species/families/genera queries
               (e.g., "Mammalia", "Felis", "Canis familiaris", or NCBI ID like "9615")
               PROVIDE this if query mentions organism/taxon/rank!
        assembly: Assembly accession for assembly-based queries (e.g., "GCF_000002305.6")
                  PROVIDE this if query mentions genome assembly!
        sample: Sample accession for sample-based queries (e.g., "SRR1234567")
                PROVIDE this if query mentions DNA/RNA sample!
        rank: Taxonomic rank for taxon queries (e.g., "species", "family", "genus")
              Only used when taxon is provided
        attributes: List of attribute filters with optional modifiers/operators/values
                   Each dict: {"name": "...", "operator": "...", "value": "...", "modifier": ...}
                   modifier can be string ("missing", "direct") or list (["min", "direct"])
        intent: Result type - "count" (default), "table", "histogram", or "record"

    Returns:
        dict with parsed components and search result
    """
    logger.info(f"goat_query called: user_query='{user_query}', taxon={taxon}, assembly={assembly}, "
                f"sample={sample}, intent={intent}")

    # Determine which ID type was provided
    search_index = None

    if taxon:
        search_index = "taxon"
    elif assembly:
        search_index = "assembly"
    elif sample:
        search_index = "sample"
    else:
        # Try to infer from query
        from .utilities import choose_search_index
        search_index = await choose_search_index(user_query)
        logger.info(f"Inferred search_index from query: {search_index}")

    # Log warnings if organism keywords found but no taxon provided
    if not taxon and search_index == "taxon":
        organism_keywords = ["mammal", "cat", "dog", "bat", "bird", "fish", "insect", "plant",
                             "primate"]
        if any(kw in user_query.lower() for kw in organism_keywords):
            logger.warning(f"⚠️ Query mentions organism but taxon not provided: '{user_query}'")
            msg = ("Did you mean to extract: 'mammal'→'Mammalia', 'cat'→'Felis', "
                   "'dog'→'Canis'?")
            logger.warning(msg)

    # Structure the parsed components
    parsed = {
        "taxon": taxon,
        "assembly": assembly,
        "sample": sample,
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
        taxon=taxon,
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
