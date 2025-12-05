from ..logging_config import get_logger
from .attributes import FIELD_CACHE, _fetch_valid_types
from .helpers.api import make_goat_request
from .helpers.constants import GOAT_API_BASE, GOAT_DESCRIPTION
from .helpers.formatting import format_result_table, rank_description
from .helpers.query import build_query_string, process_modifiers, set_exclusions
from .helpers.validation import (
    validate_attribute_name,
    validate_attribute_names,
    validate_attributes,
)

logger = get_logger(__name__)


async def goat_advanced_search(
    search_index: str = "taxon",
    taxon: str | None = None,
    rank: str | None = None,
    attributes: list[dict] | None = None,
    fields: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    show_table: bool = False,
    size: int = 5,
    user_query: str | None = None,
) -> str:
    """Advanced search for GoaT - EXPERT USE ONLY.

    ⚠️ RECOMMENDATION: Use goat_query instead for 95% of queries!
    
    goat_query is the recommended tool that handles GoaT-specific edge cases,
    modifier processing, and automatic parameter inference. Only use this
    goat_advanced_search tool if you need explicit control over all parameters
    and understand the GoaT API internals.

    This tool requires you to explicitly specify all parameters. All parameters except
    search_index are optional, allowing flexible queries.

    IMPORTANT: If using attributes or fields, you MUST first call
    get_attribute_selection_context with relevant keywords to discover and validate
    available attributes for the chosen search_index. This tool provides automatic
    disambiguation guidance for confusing cases like target_list vs sequencing_status.

    IMPORTANT: sort_by must be a valid attribute name for the chosen search_index
    or scientific_name, taxon_id, taxon_rank or *_id. If using sort_by with an
    attribute name not included in fields or attributes, you MUST first call
    get_attribute_selection_context to validate the attribute.

    CRITICAL - Choosing the search_index:
    Choose based on what you want to COUNT or LIST, not what attributes you filter by:
    - Use "taxon" when counting/listing taxonomic units (species, genera, families, etc.)
      Example: "How many mammal species have chromosomal assemblies" → taxon (counting species)
    - Use "assembly" ONLY when counting/listing assemblies themselves
      Example: "How many assemblies exist for mammals" → assembly (counting assemblies)
    - Use "sample" ONLY when counting/listing samples themselves
      Example: "How many samples are there for bats" → sample (counting samples)

    If uncertain, use the choose_search_index tool or default to "taxon".

    CRITICAL - Setting the rank parameter:
    When the user query mentions a taxonomic rank, you MUST provide it in the rank parameter:
    - "How many mammal SPECIES..." → rank="species"
    - "Which bat FAMILIES..." → rank="family"
    - "List GENERA in..." → rank="genus"
    - "How many ORDERS..." → rank="order"
    Common ranks: species, genus, family, order, class, phylum, kingdom, superkingdom

    Query Types by search_index:
    - taxon (default): Query taxonomic data
        * Can use: taxon, rank, and/or attributes
        * Examples: "species in Mammalia", "families with assemblies"
    - assembly: Query genome assemblies
        * Can use: taxon, and/or attributes (rank less common)
        * Examples: "assemblies with chromosome-level quality"
    - sample: Query sequencing samples
        * Can use: taxon, and/or attributes (rank less common)
        * Examples: "samples with RNA-seq data"

    CRITICAL - Using the taxon parameter:
    - ALWAYS use scientific names (e.g., "Mammalia", "Felidae", "Canis")
    - If the user provides a common name (e.g., "mammals", "cats", "dogs"),
      you MUST first translate it to a scientific name:
      * "mammals" → "Mammalia"
      * "cats" → "Felidae" (family) or "Felis" (genus)
      * "dogs" → "Canidae" (family) or "Canis" (genus)
    - RECOMMENDED: Use check_taxon_exists tool to validate the scientific name
      before calling search_goat, especially for unfamiliar taxa or when uncertain.
    - The taxon parameter supports:
      * Scientific names (default)
      * Taxon IDs
      * Partial names with wildcard * (e.g., "Canis*")
      * Name class prefixes: 'common name:dog', 'synonym:...', 'tolid prefix:...'

    For attributes:
    - Include 'operator' and 'value' keys for filtering
    - Valid operators: '=', '!=', '>', '<', '>=', '<=', 'exists'

    CRITICAL - AND vs OR logic:
    - SEPARATE attribute dicts = logical AND ("both X and Y")
    Example for "both DToL and CANBP target lists":
    [{"name": "long_list", "value": "dtol"}, {"name": "long_list", "value": "canbp"}]
    - COMMA-SEPARATED values in ONE dict = logical OR ("either X or Y")
    Example for "either DToL or CANBP target lists":
    [{"name": "long_list", "value": "dtol,canbp"}]
    - User keywords indicating AND: "both", "and", "all of", "in both", "on both"
    - User keywords indicating OR: "either", "or", "any of", "in any"

    - Taxon names: comma-separated names = OR. IMPORTANT: it is more efficient to
        search with a comma-separated list of taxon names (up to 100 at a time) than
        to do multiple separate queries.
    - Prefix values with '!' for NOT. Works with keyword attributes and taxon names.
    - If the only value(s) for a keyword attribute is negated (e.g., '!value'),
        the LLM MUST set 'null' as an additional value to include records
        where the attribute is missing.
    - Use enum values from attribute metadata when available. If a user query
        implies a specific value that is not in the enum, the LLM should use the
        value_metadata from the attribute context to infer the correct value. If
        no value can be found that matches the enum, the LLM MUST inform the user.
    - CRITICAL - Testing for attribute presence/absence:
        * To test if an attribute has ANY value: use name only, leave operator and value blank
        * NEVER use >0, >=0, <0, or <=0 to test for presence - this is INVALID
        * Only use comparison operators when the user explicitly mentions a threshold
        * Example: "species with chromosome number" = {"name": "chromosome_number"}
        * Example: "chromosome number > 20" = {"name": "chromosome_number",
        "operator": ">", "value": "20"}
    - For the taxon index only, attribute status can be "Direct", "Descendant",
        "Ancestral", or "Missing". User queries may refer to these statuses explicitly:
        * "species WITH genome_size" → records where status = Direct or Descendant
        * "species MISSING genome_size" → records where status = Missing
        * "species WITHOUT genome_size" → same as MISSING
        When you detect these keywords, set the 'exclude' key appropriately:
        * For presence ("WITH", "HAVE", etc.): exclude=['Ancestral', 'Missing']
        * For absence ("MISSING", "WITHOUT", etc.): exclude=['Direct', 'Descendant']
        Example for "species missing genome_size":
        [{"name": "genome_size", "exclude": ["Direct", "Descendant"]}]
    - For other queries where presence matters but status isn't specified,
        the LLM MUST use 'exclude': ['Ancestral', 'Missing'] to ensure only
        records with direct or descendant data are counted.

    When summarizing results or presenting a table, the LLM MUST include the GoaT
    web interface URL.
`
    Args:
        search_index: Index to search (taxon, assembly, or sample).
                      Choose based on what you're counting/listing:
                      - "taxon" for species/genera/families (default)
                      - "assembly" for genome assemblies only
                      - "sample" for sequencing samples only
                      Use choose_search_index tool if uncertain.
        taxon: Optional taxonomic scope (scientific name, taxon ID, etc.)
        rank: Optional taxonomic rank filter (e.g., species, genus, family, order, class, phylum)
              NOTE: If not provided but present in user_query, will be auto-extracted.
        attributes: Optional list of attribute filters, each with 'name'
            and optional 'operator', 'value', 'exclude' and 'include' keys
        fields: Optional list of fields to include in the response. If not provided,
            default fields are included.
        sort_by: Optional attribute name to sort results by
        sort_order: Optional sort order ('asc' or 'desc', default: 'asc')
        show_table: Whether to show results in a table format (default: False shows count)
        size: Number of rows to include in the table if show_table is True (default: 5)
        user_query: Original user query - helps auto-extract rank if not explicitly provided.
                    CRITICAL: ALWAYS provide the original user query string here.
    """
    logger.info(f"search_goat called: index={search_index}, taxon={taxon}, rank={rank}, "
                f"attributes={attributes}, fields={fields}, sort_by={sort_by}, "
                f"sort_order={sort_order}, show_table={show_table}, size={size}, "
                f"user_query={user_query}")

    # Validate that user_query is provided
    if user_query is None or not user_query.strip():
        return """Error: The 'user_query' parameter is required but was not provided.

CRITICAL: You MUST always include the original user question in the user_query parameter
when calling search_goat. This allows automatic extraction of taxonomic rank and other
parameters from the natural language query.

Example:
search_goat(
    search_index="taxon",
    taxon="Mammalia",
    user_query="How many mammal species have genome size data"
)

Please retry the call with the user_query parameter included."""

    # Auto-extract rank from user_query if not provided
    if rank is None and search_index == "taxon":
        rank_keywords = {
            'species': 'species',
            'genus': 'genus',
            'genera': 'genus',
            'family': 'family',
            'families': 'family',
            'order': 'order',
            'orders': 'order',
            'class': 'class',
            'classes': 'class',
            'phylum': 'phylum',
            'phyla': 'phylum',
            'kingdom': 'kingdom',
            'kingdoms': 'kingdom',
            'superkingdom': 'superkingdom',
            'superkingdoms': 'superkingdom',
        }
        query_lower = user_query.lower()
        for keyword, rank_value in rank_keywords.items():
            if keyword in query_lower:
                rank = rank_value
                logger.info(f"Auto-extracted rank='{rank}' from user_query")
                break

    # Warn if rank might be missing for taxon queries
    if search_index == "taxon" and rank is None and (taxon is not None or attributes is not None):
        logger.warning(
            "IMPORTANT: search_goat called with search_index='taxon' but no rank parameter. "
            "If the user query mentions a taxonomic rank (species, genus, family, order, etc.), "
            "the rank parameter should be provided. Example: rank='species' for queries about species."
        )

    # Populate FIELD_CACHE before validation
    await _fetch_valid_types(search_index)

    try:
        if attributes is not None:
            attributes = validate_attributes(attributes, search_index, FIELD_CACHE)
        if fields is not None:
            fields = validate_attribute_names(fields, search_index, FIELD_CACHE)
        if sort_by is not None:
            sort_by = validate_attribute_name(sort_by, search_index, FIELD_CACHE)
    except ValueError as ve:
        logger.error(f"Attribute validation error: {ve}")
        return f"""Error in attribute validation: {str(ve)}

Please check attribute names, operators, and values against GoaT metadata
using the get_attribute_selection_context or get_valid_types tools.
"""
    
    # Process modifiers: convert status-based modifiers to exclusions, keep summary modifiers in attributes
    if attributes is not None:
        attributes = process_modifiers(attributes)
        logger.info(f"Processed modifiers in {len(attributes)} attributes")
    
    query_string = build_query_string(taxon, rank, attributes)
    exclusions = set_exclusions(attributes)
    logger.info(f"Built query_string: {query_string}")
    logger.info(f"Built exclusions: {exclusions}")

    endpoint = "search" if show_table else "count"

    if query_string:
        url = (
            f"{GOAT_API_BASE}/{endpoint}?query={query_string}"
            f"&result={search_index}&offset=0&includeEstimates=true&taxonomy=ncbi"
            f"{exclusions}"
        )
    else:
        # Empty query - count/show all records in index
        url = f"{GOAT_API_BASE}/{endpoint}?result={search_index}&offset=0&includeEstimates=true&taxonomy=ncbi"

    url += f"&size={size}&report=sources"
    if fields:
        url += "&fields=" + "%2C".join(fields)
    if sort_by:
        url += f"&sortBy={sort_by}"
        if sort_order and sort_order.lower() in ["asc", "desc"]:
            url += f"&sortOrder={sort_order.lower()}"

    data = await make_goat_request(url)

    # Format response based on what was queried
    if show_table:
        if not data or "results" not in data:
            return f"Unable to fetch results or no results found for URL: {url}."
        count = data.get("status", {}).get("hits", 0)
        search_url = url.replace("/api/v2", "")
    else:
        if not data or "count" not in data:
            return f"Unable to fetch count or no count found for URL: {url}."
        count = data.get("count", 0)
        search_url = url.replace("/api/v2", "").replace("count?", "search?")

    if taxon and rank:
        description = f"{count} {rank_description(rank)} within {taxon}"
    elif taxon:
        description = f"{count} records within {taxon}"
    elif rank:
        description = f"{count} {rank_description(rank)}"
    else:
        index_name = {"taxon": "taxa", "assembly": "assemblies", "sample": "samples"}.get(
            search_index, "records"
        )
        description = f"{count} {index_name}"

    if attributes:
        description += " matching the specified attributes"

    table = ""
    if show_table and "results" in data:
        table = format_result_table(
            data["results"],
            search_fields=fields or [],
            search_url=search_url,
        )

    result = f"""
According to {GOAT_DESCRIPTION}, there are {description}.

This count is based on data from the NCBI taxonomy,
supplemented by additional metadata from the GoaT database.
"""

    if show_table:
        return f"""

This table shows the top {size} results.

{table}
"""

    result += f"""

Explore these results in the GOAT web interface:
{search_url}
"""

    return result


def register_tools(mcp) -> None:
    """Register GoaT search tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(goat_advanced_search)
