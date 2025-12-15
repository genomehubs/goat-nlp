from ..logging_config import get_logger
from .helpers.api import make_goat_request
from .helpers.constants import FIELD_CACHE, GOAT_API_BASE
from .helpers.fetch import fetch_valid_types
from .helpers.formatting import format_result_table, rank_description
from .helpers.query import build_query_string, process_modifiers, set_exclusions
from .helpers.validation import (  # validate_attribute_names,
    validate_attribute_name,
    validate_attributes,
)

logger = get_logger(__name__)


async def goat_advanced_search(
    search_index: str = "taxon",
    taxa: list[str] | None = None,
    taxon_filter_type: str = "children",
    assemblies: list[str] | None = None,
    samples: list[str] | None = None,
    rank: str | None = None,
    attributes: list[dict] | None = None,
    fields: list[dict] | None = None,
    names: list[str] | None = None,
    ranks: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    show_table: bool = False,
    size: int = 5,
    page: int = 1,
    user_query: str | None = None,
) -> str:
    """Advanced search for GoaT

    Args:
        search_index: Index to search (taxon, assembly, or sample).
                      Choose based on what you're counting/listing:
                      - "taxon" for species/genera/families (default)
                      - "assembly" for genome assemblies only
                      - "sample" for sequencing samples only
                      Use choose_search_index tool if uncertain.
        taxa: Optional taxonomic scope (scientific name, taxon ID, etc.)
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
        page: Page number for pagination (default: 1)
        user_query: Original user query - helps auto-extract rank if not explicitly provided.
                    CRITICAL: ALWAYS provide the original user query string here.
    """
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
    if search_index == "taxon" and rank is None and (taxa is not None or attributes is not None):
        logger.warning(
            "IMPORTANT: search_goat called with search_index='taxon' but no rank parameter. "
            "If the user query mentions a taxonomic rank (species, genus, family, order, etc.), "
            "the rank parameter should be provided. Example: rank='species' for queries about species."
        )

    # Populate FIELD_CACHE before validation
    await fetch_valid_types(search_index)

    try:
        if attributes is not None:
            attributes = validate_attributes(attributes, search_index, FIELD_CACHE)
        if fields is not None:
            fields = validate_attributes(fields, search_index, FIELD_CACHE, is_field=True)
        if sort_by is not None and sort_by != "":
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

    filtered_names = []
    extra_taxa = []
    taxa_length_before = len(taxa or [])
    for name in names or []:
        parts = name.split(":")
        if len(parts) == 2:
            if parts[0].replace("_", " ") in {
                "common name", "synonym", "tolid prefix", "authority"
            }:
                taxa.append(f"{parts[0].replace('_', ' ')}:{parts[1]}")
            elif parts[0].replace("_", " ") == "scientific name":
                extra_taxa.extend(parts[1].split(","))
                filtered_names.append(name)
        else:
            filtered_names.append(name)
    if len(filtered_names) != len(names or []):
        if taxa_length_before == 0:
            taxon_filter_type = "matching"
        elif taxon_filter_type != "matching":
            return """Error: prefixed names in 'names' (e.g., 'common name:dog') cannot be used
            alongside regular taxon names in 'taxa' unless taxon_filter_type is set to 'matching'.

            Please check with the user and retry the call with taxon_filter_type='matching' ONLY if
            it is valid to do so."""

    names = filtered_names
    taxa = (taxa or []) + extra_taxa

    query_string = build_query_string(taxa, rank, attributes, assemblies, samples, taxon_filter_type)
    exclusions = set_exclusions(attributes)
    logger.info(f"Built query_string: {query_string}")
    logger.info(f"Built exclusions: {exclusions}")

    endpoint = "search" if show_table else "count"

    if query_string:
        url = (
            f"{GOAT_API_BASE}/{endpoint}?query={query_string}"
            f"&result={search_index}"
            f"{exclusions}"
        )
    else:
        # Empty query - count/show all records in index
        url = f"{GOAT_API_BASE}/{endpoint}?result={search_index}"
    if size is not None:
        url += f"&size={size}&offset={(page - 1) * size}"
    url += "&includeEstimates=true&taxonomy=ncbi&report=sources"
    if fields:
        parsed_fields = []
        for field in fields:
            parsed_fields.append(field['name'])
            if "modifier" in field:
                for mod in field["modifier"]:
                    if mod not in [
                        "min", "max", "mean", "median", "mode", "length",
                        "direct", "descendant", "ancestral", "missing"
                    ]:
                        logger.warning(f"Ignoring invalid modifier '{mod}' for field '{field['name']}'")
                        continue
                    parsed_fields.append(f"{field['name']}%3A{mod}")
        url += "&fields=" + "%2C".join(parsed_fields)
    if sort_by:
        url += f"&sortBy={sort_by}"
        if sort_order and sort_order.lower() in ["asc", "desc"]:
            url += f"&sortOrder={sort_order.lower()}"
    if names:
        url += "&names=" + "%2C".join(names)
    if ranks:
        url += "&ranks=" + "%2C".join(ranks)

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

    if taxa and rank and search_index == "taxon":
        description = f"{count} {rank_description(rank)} within {','.join(taxa)}"
    elif taxa:
        description = f"{count} records within {','.join(taxa)}"
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
            search_names=names or [],
            search_ranks=ranks or [],
            search_url=search_url,
        )

    result = f"""
According to GoaT, there are {description}.

This count is based on data from the NCBI taxonomy,
supplemented by additional metadata from the GoaT database.
"""

    if show_table:
        result += f"""

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
