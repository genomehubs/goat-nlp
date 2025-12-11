"""Query parser tool for extracting structured query components from user questions."""

from typing import Any

from ..logging_config import get_logger
from .helpers.constants import FIELD_CACHE
from .helpers.fetch import fetch_valid_types
from .helpers.query import set_search_tips
from .helpers.validation import set_search_index, validate_attribute_name, validate_dict

logger = get_logger(__name__)


PROCESS_ATTRIBUTES_PROMPT = """Parse query parameters to form a GoaT URL and return optional count and table.

CRITICAL: ONLY RUN THIS TOOL AFTER PROCESSING IDENTIFIERS WITH process_identifiers()
          AND ATTRIBUTES WITH process_attributes()!
          YOU MUST PASS THE UNCHANGED IDENTIFIERS AND ATTRIBUTES OUTPUTS TO THIS TOOL AS INPUT!

GOTCHAS: The most common reason this tool fails is because the input data structures
          have been modified or incorrectly constructed. ENSURE YOU PASS THE EXACT
          OUTPUTS FROM process_identifiers() AND process_attributes() WITHOUT MODIFICATION!

FOLLOW THESE STEPS EXACTLY:

1. **identifiers_output**: Pass in the process_identifiers() output data structure EXACTLY. DO NOT MODIFY IT.

2. **attributes_output**: Pass in the process_attributes() output data structure EXACTLY. DO NOT MODIFY IT.

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
Step 1: process_identifiers() output → IDENTIFIERS_OUTPUT = {
    "taxa": ["Mammalia"],
    "assemblies": [],
    "samples": [],
    "rank": "species",
    "intent": "count",
    "taxon_filter_type": "children",
    "user_query": "How many mammal species have minimum directly measured genome size < 3G?"
}
Step 2: process_attributes() output → ATTRIBUTES_OUTPUT = {
    "attributes": [{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}],
    "fields": [],
    "intent": "count",
    "taxa": ["Mammalia"],
    "rank": "species",
    "taxon_filter_type": "children",
    "user_query": "How many mammal species have minimum directly measured genome size < 3G?"
}
THEN CALL:
goat_query(
    identifiers_output=IDENTIFIERS_OUTPUT,
    attributes_output=ATTRIBUTES_OUTPUT,
    intent="count",
    sort_by=None,
    sort_order=None,
    size=None,
    page=1
)

"""

EXTRA_DETAILS_PROMPT = """FOLLOW THESE STEPS EXACTLY:
If intent is table, ALSO PROCESS:
4. **sort_by**: Attribute name to sort results by, with optional modifier

5. **sort_order**: Sort order - "asc" or "desc"

6. **size**: Result size limit (default 10 for tables, None for counts)

7. **page**: Page number for pagination (default 1)

REMEMBER: ALWAYS PASS THE ORIGINAL IDENTIFIERS OUTPUT AS INPUT TO THIS TOOL!

8. **identifiers_output**: Pass in the identifiers output data structure EXACTLY. DO NOT MODIFY IT.


EXAMPLE:
Query: "How many mammal species have minimum directly measured genome size < 3G?"

Step 1: Attributes → [{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}]
Step 2: Fields → []
Step 3: Intent → "How many" = "count"

THEN CALL:
process_attributes(
    attributes=[{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}],
    fields=[],
    intent="count",
    identifiers_output=IDENTIFIERS_OUTPUT
)

DO NOT CALL unless you've completed all 8 steps above!
"""


async def goat_query(
    identifiers_output: dict[str, Any],
    attributes_output: dict[str, Any],
    intent: str,
    sort_by: str | None = None,
    sort_order: str | None = None,
    size: int | None = None,
    page: int = 1,
) -> dict[str, Any]:
    """Parse processed attributes and identifiers into a GoaT URL and optionally return a count and table.

    Args:
        identifiers_output: Output from process_identifiers() containing identifier-related parameters.
        attributes_output: Output from process_attributes() containing attribute-related parameters.
        intent: Result type - "count" (default), "table", "histogram", or "record"
        sort_by: Optional field to sort results by (e.g., "genome_size")
        sort_order: Optional sort order - "asc" or "desc"
        size: Optional result size limit (default 10 for tables, None for counts)
        page: Optional page number for pagination (default 1)

    Returns:
        dict with URL, count and result table (if requested)
    """

    if not validate_dict(attributes_output) or not validate_dict(identifiers_output):
        raise ValueError(
            "Invalid identifiers_output or attributes_output provided to goat_query().\n"
            "Ensure you pass the EXACT output from process_identifiers() and process_attributes()\n"
            "WITHOUT modification."
        )
    if intent not in {"count", "table", "histogram", "record"}:
        raise ValueError(
            f"""Invalid intent '{intent}' provided to goat_query().\n"""
            f"""Valid intents are: "count", "table", "histogram", or "record"."""
        )

    taxa = identifiers_output.get("taxa", [])
    assemblies = identifiers_output.get("assemblies", [])
    samples = identifiers_output.get("samples", [])
    taxon_filter_type = identifiers_output.get("taxon_filter_type", "children")
    rank = identifiers_output.get("rank")
    user_query = identifiers_output.get("user_query", "")

    search_index = await set_search_index(
        taxa, assemblies, samples, user_query
    )

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
        attributes_output.get("attributes"),
        attributes_output.get("fields"),
        attributes_output.get("intent"),
    )

    return {
        "user_query": attributes_output.get("user_query", ""),
        "result": result,
        "search_tips": search_tips,
    }


# Set the runtime docstring / tool description to the selected LLM prompt.
goat_query.__doc__ = PROCESS_ATTRIBUTES_PROMPT


def register_tools(mcp) -> None:
    """Register query parser tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(goat_query)
