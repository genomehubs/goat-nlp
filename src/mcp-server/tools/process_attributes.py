"""Process attributes tool for preparing attribute-related query parameters."""

from typing import Any

from ..logging_config import get_logger
from .helpers.constants import FIELD_CACHE
from .helpers.fetch import fetch_valid_types
from .helpers.validation import hash_dict, set_search_index, validate_attributes
from .utilities import fetch_valid_ranks

logger = get_logger(__name__)

PROCESS_ATTRIBUTES_PROMPT = """Process and validate attribute-related query parameters for GoaT API queries.

Follow the procedure below to extract and format the attributes correctly. Ignore any other information, this
will be handled in other steps.

IMPORTANT: names passed to attributes, fields and sortby MUST be valid attribute names.
You can check attribute names using get_attribute_selection_context() if needed.

REMEMBER: A user query may request multiple attributes, fields, names, and ranks.
An LLM MUST be decide if a name is an attribute filter, a field to return, a taxon name class, or a taxonomic rank
based on the context of the user query.

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

3. **names**: Taxon name classes to include in the response.
   Examples:
   - "show scientific names ..." → ["scientific_name"]
   - "return common name and synonym for ..." → ["common_name", "synonym"]
   - "list the tolid prefix and authority for ..." → ["tolid_prefix", "other_name"]

4. **ranks**: Taxonomic ranks to include in the response.
   These are ranks that the user request to be returned as fields.
   There is no need to include a rank used for filtering unless it is also requested as a field.
   IMPORTANT these MUST be valid rank names (Use get_valid_ranks() to check) for unusual ranks.
   Always use singular forms.
   Examples:
   - "return the species ..." → ["species"]
   - "get me the genus and family ..." → ["genus", "family"]

5. **user_query**: Copy the original question EXACTLY. DO NOT MODIFY IT.

EXAMPLE:
Query: "How many mammal species have minimum directly measured genome size < 3G?"

Step 1: Attributes → [{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}]
Step 2: Fields → []
Step 3: Names → []
Step 4: Ranks → []
Step 5: user_query → Copy exactly

THEN CALL:
process_attributes(
    attributes=[{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}],
    fields=[],
    names=[],
    ranks=[],
    user_query="How many mammal species have minimum directly measured genome size < 3G?"
)

DO NOT CALL unless you've completed all 5 steps above!
"""


async def process_attributes(
    attributes: list[dict[str, Any]],
    fields: list[dict[str, Any]],
    user_query: str,
    names: list[str] | None = None,
    ranks: list[str] | None = None,
) -> dict[str, Any]:
    """Process and validate attribute-related query parameters.

    Args:
        attributes: List of attribute filter dicts with 'name' and optional 'operator', 'value', and 'modifier'.
        fields: List of attribute field dicts with 'name' and optional 'modifier'.
        user_query: The original user question
        names: Optional list of taxon name classes to include in the response.
        ranks: Optional list of taxonomic ranks to include in the response.

    Returns:
        A dictionary with processed attributes for GoaT API queries.
"""

    search_index = await set_search_index([], [], [], user_query) or "taxon"

    # Populate FIELD_CACHE before validation
    await fetch_valid_types(search_index)

    try:
        if attributes:
            validate_attributes(attributes, search_index=search_index, field_cache=FIELD_CACHE)
        if fields:
            validate_attributes(fields, search_index=search_index, field_cache=FIELD_CACHE)
    except ValueError as e:
        raise ValueError(
            f"""Validation error in process_attributes(): {e}

Ensure attribute and field names are valid for the '{search_index}' index.
You can check valid attribute names using get_attribute_selection_context()."""
        ) from e

    valid_names = {"scientific_name", "common_name", "synonym", "tolid_prefix", "authority"}
    if names:
        for name in names:
            if name not in valid_names:
                raise ValueError(
                    f"""Invalid name '{name}' provided to process_attributes().
Valid names are: {', '.join(valid_names)}."""
                )
    if ranks:
        valid_ranks = await fetch_valid_ranks()
        for rank in ranks:
            if rank not in valid_ranks:
                raise ValueError(
                    f"""Invalid rank '{rank}' provided to process_attributes().
Valid ranks are: {', '.join(valid_ranks)}."""
                )

    # Ensure fields is a list
    fields = fields or []

    # Build a map of existing fields by name to avoid duplicates and preserve order
    fields_by_name: dict[str, dict[str, Any]] = {}
    ordered_field_names: list[str] = []
    for f in fields:
        name = f.get("name")
        if not name:
            continue
        mods = f.get("modifier", [])
        if isinstance(mods, str):
            mods = [mods]
        # preserve order and uniqueness
        mods = list(dict.fromkeys(mods))
        fields_by_name[name] = {"name": name, "modifier": mods}
        ordered_field_names.append(name)

    # Merge attributes into fields, adding modifiers without creating duplicates
    for attr in attributes or []:
        name = attr.get("name")
        if not name:
            continue
        mods = attr.get("modifier", [])
        if isinstance(mods, str):
            mods = [mods]

        if name not in fields_by_name:
            fields_by_name[name] = {"name": name, "modifier": []}
            ordered_field_names.append(name)

        existing_mods = fields_by_name[name].setdefault("modifier", [])
        for m in mods:
            if m not in existing_mods:
                existing_mods.append(m)

    # Rebuild the fields list preserving original order, then new fields
    new_fields: list[dict[str, Any]] = [fields_by_name[name] for name in ordered_field_names]

    result: dict[str, Any] = {
        "attributes": attributes,
        "fields": new_fields,
        "user_query": user_query,
        "names": names or [],
        "ranks": ranks or [],
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
