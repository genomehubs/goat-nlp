"""Simplified search interface for common GoaT queries."""

from ..logging_config import get_logger
from .search import goat_advanced_search

logger = get_logger(__name__)


async def goat_simple_search(
    user_query: str,
    what_to_count: str | None = None,
    taxon: str | None = None,
    specific_attribute: str | None = None,
) -> str:
    """Simple search interface for basic GoaT queries.

    ⚠️ RECOMMENDATION: Use goat_query for better results!

    goat_query provides better handling of complex queries, modifiers, and
    edge cases. Only use goat_simple_search for the most basic queries.

    CRITICAL: Always provide user_query - it helps us understand your question.

    For most queries, you only need to provide:
    1. user_query: The original question (required)
    2. what_to_count: What you're counting - choose ONE:
       - "species" - "How many SPECIES..."
       - "genus/genera" - "How many GENERA..."
       - "family/families" - "Which FAMILIES..."
       - "order/orders" - "How many ORDERS..."
       - "assemblies" - "How many ASSEMBLIES..."
       - "samples" - "How many SAMPLES..."
    3. taxon: Optional taxonomic scope (scientific name)
       For common names, use these translations:
       - "dog/dogs" → "Canis"
       - "cat/cats" → "Felis"
       - "bat/bats" → "Chiroptera"
       - "mammal/mammals" → "Mammalia"
       - "bird/birds" → "Aves"
       - "fish" → "Actinopterygii"
       - "insect/insects" → "Insecta"
       - "plant/plants" → "Plantae"
       - "flowering plant" → "Magnoliopsida"

    Examples:
    - "How many cat species have genome size data?"
      what_to_count="species", taxon="Felis"
    - "Which bat families are targeted by VGP?"
      what_to_count="families", taxon="Chiroptera"
    - "Show assemblies for dogs"
      what_to_count="assemblies", taxon="Canis"

    If you need to filter by a specific attribute (like "genome size", "assembly level"),
    provide specific_attribute with the exact attribute name. For complex queries with
    multiple filters, use search_goat instead.

    Args:
        user_query: The original user question (required)
        what_to_count: What you're counting (species/families/genera/orders/assemblies/samples)
        taxon: Optional scientific name to scope the search
        specific_attribute: Optional attribute name to filter by
    """
    logger.info(
        f"simple_search called: what_to_count={what_to_count}, taxon={taxon}, "
        f"specific_attribute={specific_attribute}, user_query={user_query}"
    )

    # Map what_to_count to search_index and rank
    search_index_map = {
        "species": ("taxon", "species"),
        "genus": ("taxon", "genus"),
        "genera": ("taxon", "genus"),
        "family": ("taxon", "family"),
        "families": ("taxon", "family"),
        "order": ("taxon", "order"),
        "orders": ("taxon", "order"),
        "class": ("taxon", "class"),
        "classes": ("taxon", "class"),
        "phylum": ("taxon", "phylum"),
        "phyla": ("taxon", "phylum"),
        "kingdom": ("taxon", "kingdom"),
        "kingdoms": ("taxon", "kingdom"),
        "assemblies": ("assembly", None),
        "assembly": ("assembly", None),
        "samples": ("sample", None),
        "sample": ("sample", None),
    }

    search_index = "taxon"
    rank = None

    if what_to_count:
        what_lower = what_to_count.lower().strip()
        if what_lower in search_index_map:
            search_index, rank = search_index_map[what_lower]
            logger.info(f"Mapped what_to_count to search_index={search_index}, rank={rank}")

    # Build attributes if specific_attribute provided
    attributes = None
    if specific_attribute:
        attributes = [{"name": specific_attribute}]
        logger.info(f"Built attributes from specific_attribute: {attributes}")

    # Delegate to goat_advanced_search
    logger.info(
        f"Delegating to goat_advanced_search: search_index={search_index}, taxon={taxon}, "
        f"rank={rank}, attributes={attributes}"
    )
    return await goat_advanced_search(
        search_index=search_index,
        taxon=taxon,
        rank=rank,
        attributes=attributes,
        user_query=user_query,
        show_table=False,
        size=5,
    )


def register_tools(mcp) -> None:
    """Register simple search tool with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(goat_simple_search)
