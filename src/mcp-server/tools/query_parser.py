"""Query parser tool for extracting structured query components from user questions."""

from typing import Any

from ..logging_config import get_logger
from .helpers.query import set_search_tips
from .helpers.validation import validate_dict

logger = get_logger(__name__)


PROCESS_ATTRIBUTES_PROMPT = """Parse query parameters to form a GoaT URL and return optional count and table.

CRITICAL: ONLY RUN THIS TOOL AFTER PROCESSING IDENTIFIERS WITH process_identifiers()
          AND ATTRIBUTES WITH process_attributes()!
          YOU MUST PASS THE UNCHANGED ATTRIBUTES OUTPUT TO THIS TOOL AS INPUT!

FOLLOW THESE STEPS EXACTLY:

1. **attribute_output**: Output of the process_attributes() tool. DO NOT MODIFY IT.

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
Step 2: process_attributes() output → attributes_output = {
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
    attributes_output=attributes_output
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
    attributes_output: dict[str, Any],
    # sort_by: str | None = None,
    # sort_order: str | None = None,
    # size: int | None = None,
    # page: int = 1,
) -> dict[str, Any]:
    """Parse processed attributes and identifiers into a GoaT URL and optionally return a count and table.

    Args:
        attributes_output: Output from process_attributes() containing all parameters.
        # sort_by: Optional field to sort results by (e.g., "genome_size")
        # sort_order: Optional sort order - "asc" or "desc"
        # size: Optional result size limit (default 10 for tables, None for counts)
        # page: Optional page number for pagination (default 1)

    Returns:
        dict with URL, count and result table (if requested)
    """

    if not validate_dict(attributes_output):
        raise ValueError(
            "Invalid attributes_output provided to goat_query().\n"
            "Ensure you pass the EXACT output from process_attributes() without modification."
        )

    # Import here to avoid circular dependency
    from .search import goat_advanced_search

    # Delegate to goat_advanced_search with the parsed components
    result = await goat_advanced_search(
        user_query=attributes_output.get("user_query", ""),
        search_index=attributes_output.get("search_index", "taxon"),
        taxa=attributes_output.get("taxa"),
        taxon_filter_type=attributes_output.get("taxon_filter_type"),
        assemblies=attributes_output.get("assemblies"),
        samples=attributes_output.get("samples"),
        rank=attributes_output.get("rank"),
        attributes=attributes_output.get("attributes"),
        fields=attributes_output.get("fields"),
        show_table=(attributes_output.get("intent") == "table"),
        size=attributes_output.get("size") if attributes_output.get("intent") == "table" else None,
        sort_by=attributes_output.get("sort_by"),
        sort_order=attributes_output.get("sort_order"),
        page=attributes_output.get("page"),
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
