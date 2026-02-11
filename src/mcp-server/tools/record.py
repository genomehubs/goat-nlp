from typing import Any

from ..config import API_BASE, DATASTORE_NAME
from ..logging_config import get_logger
from .helpers.api import make_api_request
from .helpers.constants import FIELD_CACHE
from .helpers.fetch import fetch_valid_types
from .helpers.formatting import format_record
from .helpers.validation import validate_attribute_names

logger = get_logger(__name__)


async def get_record(
    record_id: str,
    search_index: str,
    attributes: list[str] | None = None,
    truncate: bool = True,
) -> Any:
    f"""Get a single record from {DATASTORE_NAME}.

     ⚠️ RECOMMENDATION: IF the user query involves multiple records or complex
     filters, Use submit_query instead to retrieve a table for 95% of queries!

    An LLM can use this to fetch detailed information about a specific record.
    the record ID can be a taxon ID, assembly accession, or sample ID depending
    on the search_index.

    Use this tool after identifying a specific record of interest from a submit_query
    search, or when a use explicitly requests information about a known record.

    Example user queries that would use this tool:
    - "Give me details about the taxon with ID 1234."
    - "What is the assembly level and genome size for assembly GCA_123456?"
    - "What information does have about bats?" (Implies fetching record for order
        Chiroptera.)
    - "What target lists are cats on?" (Implies fetching record for family Felidae.)
    - "Provide details about sample SRS123456."
    - "Which bioprojects are associated with rodents?" (Implies fetching record for
        order Rodentia.)
    - "what is the full lineage of Canis lupus?" (Implies fetching record for taxon
        Canis lupus with an empty attribute list, [].)

    Returned information includes:
    - Scientific name
    - Taxon ID
    - Rank
    - Lineage
    - Requested attributes and their values

    When summarizing a record, the LLM MUST include the {DATASTORE_NAME} web interface URL.

    Args:
        record_id: ID of the record to fetch
        search_index: Index type (taxon, assembly, sample)
        attributes: List of attributes to include in the response (default: all)
        truncate: Whether to truncate long lists of attribute values (default: True)
    """
    # Populate FIELD_CACHE before validation
    await fetch_valid_types(search_index)

    try:
        if attributes is not None:
            attributes = validate_attribute_names(attributes, search_index, FIELD_CACHE)
    except ValueError as ve:
        return f"""Error in attribute validation: {str(ve)}

Please check attribute names against {DATASTORE_NAME} metadata using the
get_attribute_selection_context or get_valid_types tools.
"""
    url = (
        f"{API_BASE}/record?result={search_index}"
        f"&recordId={record_id}&taxonomy=ncbi"
    )
    data = await make_api_request(url)
    if not data or "records" not in data:
        return {"error": "Unable to fetch record or no record found."}

    return format_record(data["records"][0]["record"], url, attributes, truncate)


def register_tools(mcp) -> None:
    f"""Register {DATASTORE_NAME} record tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(get_record)
