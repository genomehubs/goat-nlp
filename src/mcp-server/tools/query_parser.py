"""Query parser tool for extracting structured query components from user questions."""

from typing import Any

from ..config import DATASTORE_NAME
from ..logging_config import get_logger
from .artifact_store import retrieve
from .helpers.constants import FIELD_CACHE
from .helpers.fetch import fetch_valid_types
from .helpers.query import set_search_tips
from .helpers.validation import validate_attribute_name

logger = get_logger(__name__)


SUBMIT_QUERY_PROMPT = f"""Parse query parameters to form a {DATASTORE_NAME} URL and return results.

⚠️  CRITICAL: Pass the EXACT artifact keys from process_identifiers() and process_attributes()
   WITHOUT any modification. Do not reconstruct these objects yourself.

PARAMETERS:

1. **identifiers_artifact_id**: Output key from process_identifiers()

2. **attributes_artifact_id**: Output key from process_attributes()

3. **intent**: Type of result (choose one)
   - "count": Total count only
   - "table": Paginated results + count (single query - do not call again for count!)
   - "sources": Data sources + count (single query)

4. **sort_by**: (for intent="table") Field to sort by (e.g., "genome_size")

5. **sort_order**: (for intent="table") "asc" or "desc"

6. **size**: (for intent="table") Limit results (default 10)

7. **page**: (for intent="table") Page number (default 1)


EXAMPLE:
Query: "How many mammal species have minimum directly measured genome size < 3G?"

submit_query(
    identifiers_artifact_id="aebc12345...",
    attributes_artifact_id="fghd67890...",
    intent="count"
)

To get results as a table (which includes the count):

submit_query(
    identifiers_artifact_id="aebc12345...",
    attributes_artifact_id="fghd67890...",
    intent="table",
    size=10,
    page=1
)

"""


async def submit_query(
    identifiers_artifact_id: str,
    attributes_artifact_id: str,
    intent: str,
    search_index: str = "taxon",
    sort_by: str | None = None,
    sort_order: str | None = None,
    size: int | None = None,
    page: int = 1,
) -> dict[str, Any]:
    f"""Parse processed attributes and identifiers into a {DATASTORE_NAME} URL and return results.

    IMPORTANT: intent="table" returns BOTH count AND results in a single query.
               Do NOT call this tool twice for count+table - use intent="table" once.

    Args:
        identifiers_artifact_id: Artifact id from process_identifiers() containing identifier-related parameters.
        attributes_artifact_id: Artifact id from process_attributes() containing attribute-related parameters.
        intent: Result type - "count" (just count), "table" (count + paginated
            results), or "sources" (count + data sources)
        search_index: The search index to use ("taxon", "assembly", or "sample")
        sort_by: Optional field to sort results by (e.g., "genome_size") - only used with intent="table"
        sort_order: Optional sort order - "asc" or "desc" - only used with intent="table"
        size: Optional result size limit (default 10 for tables)
        page: Optional page number for pagination (default 1, only for intent="table")

    Returns:
        dict with result field containing:
        - For intent="count": count value
        - For intent="table": count and paginated table of results
        - For intent="sources": count and list of data sources
    """

    # If artifact tokens were provided (string), attempt to retrieve stored objects
    if isinstance(identifiers_artifact_id, str):
        identifiers_output = retrieve(identifiers_artifact_id)
    if isinstance(attributes_artifact_id, str):
        attributes_output = retrieve(attributes_artifact_id)

    if not isinstance(identifiers_output, dict):
        raise ValueError(
            "Invalid identifiers_artifact_id provided to submit_query().\n"
            "Ensure you pass the EXACT key from process_identifiers()\n"
            "WITHOUT modification.\n\n"
            "Note that the identifiers artifact is only valid for a limited time after creation.\n"
            "If it has expired, you will need to re-run process_identifiers() to get a new artifact key."
        )
    if not isinstance(attributes_output, dict):
        raise ValueError(
            "Invalid attributes_artifact_id provided to submit_query().\n"
            "Ensure you pass the EXACT key from process_attributes()\n"
            "WITHOUT modification.\n\n"
            "Note that the attributes artifact is only valid for a limited time after creation.\n"
            "If it has expired, you will need to re-run process_attributes() to get a new artifact key."
        )

    if intent not in {"count", "sources", "table"}:
        if intent in {"histogram", "scatter", "tree", "donut", "rainbow"}:
            raise ValueError(
                f"""Intent '{intent}' is not currently supported by submit_query().\n"""
                f"""For these types of results, use get_report() instead with the appropriate report_type."""
            )
        else:
            raise ValueError(
                f"""Invalid intent '{intent}' provided to submit_query().\n"""
                f"""Valid intents are: "count", "table" or "sources"."""
            )

    taxa = identifiers_output.get("taxa", [])
    assemblies = identifiers_output.get("assemblies", [])
    samples = identifiers_output.get("samples", [])
    taxon_filter_type = identifiers_output.get("taxon_filter_type", "children")
    rank = identifiers_output.get("rank")
    user_query = identifiers_output.get("user_query", "")

    show_table = intent == "table"
    show_sources = intent == "sources"

    if show_table:
        if size is None:
            size = 10  # Default size for tables
        if sort_by:
            try:
                sort_by = sort_by.split(" ")[0].split(".")[0].split(":")[0]
                await fetch_valid_types(search_index)
                validate_attribute_name(sort_by, search_index, FIELD_CACHE)
            except ValueError as ve:
                raise ValueError(
                    f"""Error in sort_by attribute validation: {str(ve)}"""
                ) from ve

    attributes = attributes_output.get("attributes", [])
    fields = attributes_output.get("fields", [])
    names = attributes_output.get("names", [])
    ranks = attributes_output.get("ranks", [])

    # Import here to avoid circular dependency
    from .search import advanced_search

    # Delegate to advanced_search with the parsed components
    result = await advanced_search(
        user_query=user_query,
        search_index=search_index,
        taxa=taxa,
        taxon_filter_type=taxon_filter_type,
        assemblies=assemblies,
        samples=samples,
        rank=rank,
        attributes=attributes,
        fields=fields,
        names=names,
        ranks=ranks,
        show_table=show_table,
        show_sources=show_sources,
        size=size if show_table else None,
        sort_by=sort_by if show_table else None,
        sort_order=sort_order if show_table else None,
        page=page if show_table else None,
    )

    search_tips = set_search_tips(
        attributes,
        fields,
        intent,
    )

    return {
        "user_query": user_query,
        "result": result,
        "search_tips": search_tips,
    }


# Set the runtime docstring / tool description to the selected LLM prompt.
submit_query.__doc__ = SUBMIT_QUERY_PROMPT


def register_tools(mcp) -> None:
    """Register query parser tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(submit_query)
