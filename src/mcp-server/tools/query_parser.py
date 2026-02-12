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


SUBMIT_QUERY_PROMPT = f"""Parse query parameters to form a {DATASTORE_NAME} URL, optionally
return a count and table.

CRITICAL: ONLY RUN THIS TOOL AFTER PROCESSING IDENTIFIERS WITH process_identifiers()
          AND ATTRIBUTES WITH process_attributes()!
          YOU MUST PASS THE UNCHANGED IDENTIFIERS AND ATTRIBUTES ARTEFACT KEYS AS INPUT!

GOTCHAS: The most common reason this tool fails is because the input data structures
          have been modified or incorrectly constructed. ENSURE YOU PASS THE EXACT
          OUTPUTS FROM process_identifiers() AND process_attributes() WITHOUT MODIFICATION!

FOLLOW THESE STEPS EXACTLY:

1. **identifiers_output**: Pass in the process_identifiers() artifact key EXACTLY. DO NOT MODIFY IT.

2. **attributes_output**: Pass in the process_attributes() artifact key EXACTLY. DO NOT MODIFY IT.

3. **intent**: What kind of result
   - "count": "How many..." (count species)
   - "table": "Which...", "List..." (show results)

If intent is table, ALSO PROCESS:
4. **sort_by**: Attribute name to sort results by, with optional modifier

5. **sort_order**: Sort order - "asc" or "desc"

6. **size**: Result size limit (default 10 for tables, None for counts)

7. **page**: Page number for pagination (default 1)


EXAMPLE:
Query: "How many mammal species have minimum directly measured genome size < 3G?"
Step 1: process_identifiers() output → IDENTIFIERS_OUTPUT = {{
    artifact_id: aebc12345...,
}}
Step 2: process_attributes() output → ATTRIBUTES_OUTPUT = {{
    artifact_id: fghd67890...,
}}
THEN CALL:
submit_query(
    identifiers_artifact_id=IDENTIFIERS_ARTIFACT_ID,
    attributes_artifact_id=ATTRIBUTES_ARTIFACT_ID,
    intent="count",
    sort_by=None,
    sort_order=None,
    size=None,
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
    f"""Parse processed attributes and identifiers into a {DATASTORE_NAME} URL, optionally return a count and table.

    Args:
        identifiers_artifact_id: Artifact id from process_identifiers() containing identifier-related parameters.
        attributes_artifact_id: Artifact id from process_attributes() containing attribute-related parameters.
        intent: Result type - "count" (default), "table", "histogram", or "record"
        search_index: The search index to use ("taxon", "assembly", or "sample")
        sort_by: Optional field to sort results by (e.g., "genome_size")
        sort_order: Optional sort order - "asc" or "desc"
        size: Optional result size limit (default 10 for tables, None for counts)
        page: Optional page number for pagination (default 1)

    Returns:
        dict with artifact_id, URL, count and result table (if requested)
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

    # if not validate_dict(attributes_output) or not validate_dict(identifiers_output):
    #     raise ValueError(
    #         "Invalid identifiers_artifact_id or attributes_artifact_id provided to submit_query().\n"
    #         "Ensure you pass the EXACT key from process_identifiers() and process_attributes()\n"
    #         "WITHOUT modification."
    #     )
    if intent not in {"count", "table", "histogram", "record"}:
        raise ValueError(
            f"""Invalid intent '{intent}' provided to submit_query().\n"""
            f"""Valid intents are: "count", "table", "histogram", or "record"."""
        )

    taxa = identifiers_output.get("taxa", [])
    assemblies = identifiers_output.get("assemblies", [])
    samples = identifiers_output.get("samples", [])
    taxon_filter_type = identifiers_output.get("taxon_filter_type", "children")
    rank = identifiers_output.get("rank")
    user_query = identifiers_output.get("user_query", "")

    show_table = intent == "table"

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
