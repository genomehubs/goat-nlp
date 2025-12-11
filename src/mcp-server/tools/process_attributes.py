"""Process attributes tool for preparing attribute-related query parameters."""

from typing import Any

from ..logging_config import get_logger
from .helpers.constants import FIELD_CACHE
from .helpers.fetch import fetch_valid_types
from .helpers.validation import (
    hash_dict,
    validate_attribute_name,
    validate_attributes,
    validate_dict,
)

logger = get_logger(__name__)

PROCESS_ATTRIBUTES_PROMPT = """Process and validate attribute-related query parameters for GoaT API queries.

CRITICAL: ONLY RUN THIS TOOL AFTER PROCESSING IDENTIFIERS WITH process_identifiers()!
          YOU MUST PASS THE UNCHANGED IDENTIFIERS OUTPUT TO THIS TOOL AS INPUT!

Follow the procedure below to extract and format the attributes correctly. Ignore any other information, this
will be handled in other steps.

IMPORTANT: names passed to attributes, fields and sortby MUST be valid attribute names.
You can check attribute names using get_attribute_selection_context() if needed.

FOLLOW THESE STEPS EXACTLY:

1. **attributes**: List of attribute filter dicts with 'name' and optional 'operator', 'value', and 'modifier'.
   Examples:
   - "genome_size < 3G" → [{"name": "genome_size", "operator": "<", "value": "3000000000"}]
   - With modifiers: "minimum directly measured genome_size"
     → [{"name": "genome_size", "modifier": ["min", "direct"]}]

   VALID OPERATORS:
   - Comparison: =, !=, <, <=, >, >=
   - Set membership: in, not in (value as comma-separated list)
   - Existence: exists

   VALID MODIFIERS:
   - Summary: min, max, median, mean, sum, list
   - Status: direct, ancestral, descendant, estimated, missing
   - MODIFIERS RULE:
     If query mentions BOTH summary (min/max/median) AND status (direct/ancestral):
     → Combine in ONE dict: modifier: ["min", "direct"]
     → NOT two separate dicts!

   VALID VALUE FORMATTING:
   - Numeric values: integers or decimals (e.g., 3000000000 for 3G)
   - String values: exact strings or patterns (e.g., "high", "medium", "low", "GCF_*")
   - valid values depend on the datatype of the attribute being filtered.
     * Use get_attribute_selection_context() to check.

   LOGICAL COMBINATIONS:
   - Combine multiple attribute filters using AND logic by including multiple dicts in the list.
     * Example: "genome_size < 3G AND assembly_level = 'complete'" →
       [{"name": "genome_size", "operator": "<", "value": "3000000000"},
        {"name": "assembly_level", "operator": "=", "value": "complete"}]
   - For OR logic, pass a list of values.
     * example: "assembly_level in ('complete', 'chromosome')" →
       [{"name": "assembly_level", "operator": "in", "value": ["complete","chromosome"]}]

2. **fields**:
   Attribute names that should be returned as columns. If a field used for filtering is also required as a field,
   include it in both lists:
   Examples:
   - "Show genome_size and assembly_level" → [{"name": "genome_size"}, {"name": "assembly_level"}]
   - "Give me minimum genome_size and directly measured assembly_level" → [{"name": "genome_size", "modifier":
     ["min"]}, {"name": "assembly_level", "modifier": ["direct"]}]

3. **intent**: What kind of result
   - "count": "How many..." (count species)
   - "table": "Which...", "List..." (show results)

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


async def process_attributes(
    attributes: list[dict[str, Any]],
    fields: list[dict[str, Any]],
    intent: str,
    identifiers_output: dict[str, Any],
    sort_by: str | None = None,
    sort_order: str | None = None,
    size: int | None = None,
    page: int = 1,
) -> dict[str, Any]:
    """Process and validate attribute-related query parameters.

    Args:
        attributes: List of attribute filter dicts with 'name' and optional 'operator', 'value', and 'modifier'.
        fields: List of attribute field dicts with 'name' and optional 'modifier'.
        intent: Result type - "count" (default), "table", "histogram", or "record"
        identifiers_output: Output from process_identifiers() containing identifier-related parameters.
        sort_by: Optional field to sort results by (e.g., "genome_size")
        sort_order: Optional sort order - "asc" or "desc"
        size: Optional result size limit (default 10 for tables, None for counts)
        page: Optional page number for pagination (default 1)

    Returns:
        A dictionary with processed attributes for GoaT API queries.
"""
    if not validate_dict(identifiers_output):
        raise ValueError("""Invalid identifiers_output provided to process_attributes().

Ensure you pass the EXACT output from process_identifiers() without modification.""")

    search_index = identifiers_output.get("search_index", "taxon")

    # Populate FIELD_CACHE before validation
    await fetch_valid_types(search_index)

    try:
        if attributes:
            validate_attributes(attributes, search_index=search_index, field_cache=FIELD_CACHE)
        if fields:
            validate_attributes(fields, search_index=search_index, field_cache=FIELD_CACHE)
        if sort_by:
            validate_attribute_name(sort_by, search_index, FIELD_CACHE)
    except ValueError as e:
        raise ValueError(
            f"""Validation error in process_attributes(): {e}

Ensure attribute and field names are valid for the '{search_index}' index.
You can check valid attribute names using get_attribute_selection_context()."""
        ) from e

    result: dict[str, Any] = {
        **identifiers_output,
        "attributes": attributes,
        "fields": fields,
        "intent": intent,
        "sort_by": sort_by if sort_by is not None else None,
        "sort_order": sort_order if sort_order is not None else "asc",
        "size": size if size is not None else 0,
        "page": page,
    }

    dict_hash = hash_dict(result)

    result["unique_id"] = dict_hash

    return result


process_attributes.__doc__ = PROCESS_ATTRIBUTES_PROMPT


def register_tools(mcp) -> None:
    """Register process attributes tools with the FastMCP instance.
    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(process_attributes)
