"""Process attributes tool for preparing attribute-related query parameters."""

from typing import Any

from ..config import DATASTORE_NAME
from ..logging_config import get_logger
from .helpers.constants import FIELD_CACHE
from .helpers.fetch import fetch_valid_types
from .helpers.processor_common import finalise_and_store
from .helpers.validation import validate_attributes
from .utilities import fetch_valid_ranks

logger = get_logger(__name__)

PROCESS_ATTRIBUTES_PROMPT = (
    f"""Process and validate attribute-related query parameters for {DATASTORE_NAME} API queries.

Follow the procedure below to extract and format the attributes correctly. Ignore any other information, this
will be handled in other steps.

If successful, this tool returns an artifact token that can be passed to submit_query().

IMPORTANT: names passed to attributes, fields and sortby MUST be valid attribute names.
You can check attribute names using get_attribute_selection_context() if needed.

REMEMBER: A user query may request multiple attributes, fields, names, and ranks.
An LLM MUST be decide if a name is an attribute filter, a field to return, a taxon name class, or a taxonomic rank
based on the context of the user query.

IMPORTANT: names and ranks MUST NOT be passed as attributes or fields.

REMEMBER: chaining attributes to see if any have 'exists' will join them with AND logic such that only records with
          values for ALL specified attributes will be returned. If this is not the desired behaviour, pass such
          attributes as fields instead to retrieve their values without filtering.

DISAMBIGUATION:
- "found in" suggests a regional list attribute filter

FOLLOW THESE STEPS EXACTLY:

1. **attributes**: List of attribute filter dicts with 'name' and optional 'operator', 'value', 'modifier'
   and 'type'. DO NOT include names or ranks here.
   Examples:
   - "genome_size < 3G" → [{{"name": "genome_size", "operator": "<", "value": "3000000000"}}]
   - With modifiers: "minimum directly measured genome_size"
     → [{{"name": "genome_size", "modifier": ["min", "direct"]}}]

   VALID OPERATORS:
   - Comparison: =, !=, <, <=, >, >=
   - Set membership: in, not in (value as comma-separated list)
   - Existence: exists, missing (no value needed)
   - Ordered keyword attributes can be searched using <, <=, >, >= operators.
     * Example: "assembly_level is chromosomal or better" →
       [{{"name": "assembly_level", "operator": ">=", "value": "chromosome"}}]

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
     * Example: "genome_size < 3G AND assembly_level = 'complete genome'" →
       [{{"name": "genome_size", "operator": "<", "value": "3000000000"}},
        {{"name": "assembly_level", "operator": "=", "value": "complete genome"}}]
     * Example: "on the long_list for DTOL and CANBP" →
         [{{"name": "long_list", "operator": "=", "value": ["DTOL"]}},
          {{"name": "long_list", "operator": "=", "value": ["CANBP"]}}]
   - For OR logic, pass a list of values.
     * example: "assembly_level in ('complete genome', 'chromosome')" →
       [{{"name": "assembly_level", "operator": "in", "value": ["complete genome","chromosome"]}}]

2. **fields**:
   Attribute names that should be returned as columns. If a field used for filtering is also required as a field,
   include it in both lists:
   Examples:
   - "Show genome_size and assembly_level" → [{{"name": "genome_size"}}, {{"name": "assembly_level"}}]
   - "Give me minimum genome_size and directly measured assembly_level" → [{{"name": "genome_size", "modifier":
     ["min"]}}, {{"name": "assembly_level", "modifier": ["direct"]}}]

3. **names**: Taxon name classes to include in the response.
   Can contain values from: scientific_name, common_name, synonym, tolid_prefix, authority.
   Examples:
   - "show scientific names ..." → ["scientific_name"]
   - "return common name and synonym for ..." → ["common_name", "synonym"]
   - "list the tolid prefix and authority for ..." → ["tolid_prefix", "other_name"]
   - "common name contains 'bat'" → ["common_name:*bat*"]
   - "synonym is 'Canis'" → ["synonym:Canis"]
   - "authority ends with 'Linnaeus'" → ["authority:*Linnaeus"]
   - "tolip_prefix does not start with ilLys" → ["tolid_prefix:!ilLys*"]

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

Step 1: Attributes → [
    {{"name": "genome_size", "operator": "<", "value": "3000000000",
      "modifier": ["min", "direct"]}}]
Step 2: Fields → []
Step 3: Names → []
Step 4: Ranks → []
Step 5: user_query → Copy exactly

THEN CALL:
process_attributes(
    attributes=[{{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}}],
    fields=[],
    names=[],
    ranks=[],
    user_query="How many mammal species have minimum directly measured genome size < 3G?"
)

DO NOT CALL unless you've completed all 5 steps above!
""")


async def process_attributes(
    attributes: list[dict[str, Any]],
    fields: list[dict[str, Any]],
    user_query: str,
    names: list[str] | None = None,
    ranks: list[str] | None = None,
    search_index: str = "taxon",
) -> dict[str, Any]:
    """Process and validate attribute-related query parameters.

    Args:
        attributes: List of attribute filter dicts with 'name' and optional 'operator', 'value', and 'modifier'.
        fields: List of attribute field dicts with 'name' and optional 'modifier'.
        user_query: The original user question
        names: Optional list of taxon name classes to include in the response.
        ranks: Optional list of taxonomic ranks to include in the response.
        search_index: The search index to use ("taxon", "assembly", or "sample")

    Returns:
        A dictionary with processed attributes for {DATASTORE_NAME} API queries.
"""

    valid_names = {"scientific_name", "common_name", "synonym", "tolid_prefix", "authority"}
    if names:
        for name in names:
            prefix = name.split(":", 1)[0] if ":" in name else name
            if prefix not in valid_names:
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

    filtered_fields = []
    names = names or []
    ranks = ranks or []
    for f in fields:
        name = f.get("name")
        if name and name not in names and name not in ranks:
            filtered_fields.append(f)
    fields = filtered_fields

    # Populate FIELD_CACHE before validation
    await fetch_valid_types(search_index)

    try:
        if attributes:
            nameless_attributes = []
            for attr in attributes:
                if attr.get("name", "") in valid_names:
                    if attr.get("value") is not None:
                        values = attr["value"]
                        if not isinstance(values, list):
                            values = [values]
                        values = [str(v).replace("* ", "*").replace(" *", "*") for v in values]
                        if attr.get("operator", "") in {"not in", "!="}:
                            # prepend '!' to each value for negation
                            values = [f"!{v}" for v in values]
                        names.append(f"{attr['name']}:{','.join(values)}")
                    else:
                        names.append(attr["name"])
                elif attr.get("name", "") in ranks:
                    ranks.append(attr["name"])
                else:
                    nameless_attributes.append(attr)
            attributes = nameless_attributes
            validate_attributes(attributes, search_index=search_index, field_cache=FIELD_CACHE)
        if fields:
            attr_fields = [
                f for f in (fields or [])
                if f.get("name") not in valid_names and f.get("name") not in ranks
            ]
            validate_attributes(attr_fields, search_index=search_index, field_cache=FIELD_CACHE)
    except ValueError as e:
        raise ValueError(
            f"""Validation error in process_attributes(): {e}

Ensure attribute and field names are valid for the '{search_index}' index.
You can check valid attribute names using get_attribute_selection_context()."""
        ) from e

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

    return finalise_and_store(result)


process_attributes.__doc__ = PROCESS_ATTRIBUTES_PROMPT


def register_tools(mcp) -> None:
    """Register process attributes tools with the FastMCP instance.
    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(process_attributes)


if __name__ == "__main__":
    import asyncio

    from .artifact_store import retrieve

    async def test_process_attributes():
        """Test examples for process_attributes."""
        print("=" * 60)
        print("Testing process_attributes")
        print("=" * 60)

        # Test 1: Basic attribute filter
        print("\n[Test 1] Basic attribute filter")
        result1 = await process_attributes(
            user_query="Species with genome_size < 3000000000",
            attributes=[{"name": "genome_size", "operator": "<", "value": "3000000000"}],
            fields=[]
        )
        print(f"  Artifact ID: {result1['artifact_id']}")
        data1 = retrieve(result1['artifact_id'])
        print(f"  Attributes: {data1['attributes']}")
        print(f"  Fields: {data1['fields']}")

        # Test 2: Attributes with modifiers
        print("\n[Test 2] Attributes with modifiers")
        result2 = await process_attributes(
            user_query="Show minimum directly measured genome_size",
            attributes=[{"name": "genome_size", "modifier": ["min", "direct"]}],
            fields=[{"name": "genome_size", "modifier": ["min", "direct"]}]
        )
        print(f"  Artifact ID: {result2['artifact_id']}")
        data2 = retrieve(result2['artifact_id'])
        print(f"  Attributes: {data2['attributes']}")
        print(f"  Fields (merged): {data2['fields']}")

        # Test 3: Multiple attributes (AND logic)
        print("\n[Test 3] Multiple attributes (AND logic)")
        result3 = await process_attributes(
            user_query="genome_size < 3G AND assembly_level = complete genome",
            attributes=[
                {"name": "genome_size", "operator": "<", "value": "3000000000"},
                {"name": "assembly_level", "operator": "=", "value": "complete genome"}
            ],
            fields=[]
        )
        print(f"  Artifact ID: {result3['artifact_id']}")
        data3 = retrieve(result3['artifact_id'])
        print(f"  Attributes (AND): {data3['attributes']}")

        # Test 4: Names and ranks
        print("\n[Test 4] Names and ranks")
        result4 = await process_attributes(
            user_query="Show scientific_name and common_name for genus and family",
            attributes=[],
            fields=[],
            names=["scientific_name", "common_name"],
            ranks=["genus", "family"]
        )
        print(f"  Artifact ID: {result4['artifact_id']}")
        data4 = retrieve(result4['artifact_id'])
        print(f"  Names: {data4['names']}")
        print(f"  Ranks: {data4['ranks']}")

        # Test 5: Name with filter pattern
        print("\n[Test 5] Name with filter pattern")
        result5 = await process_attributes(
            user_query="common_name contains 'bat'",
            attributes=[{"name": "common_name", "value": "*bat*"}],
            fields=[]
        )
        print(f"  Artifact ID: {result5['artifact_id']}")
        data5 = retrieve(result5['artifact_id'])
        print(f"  Names: {data5['names']}")
        print(f"  Attributes: {data5['attributes']}")

        # Test 6: Field deduplication
        print("\n[Test 6] Field deduplication and merging")
        result6 = await process_attributes(
            user_query="Test field merging",
            attributes=[
                {"name": "genome_size", "modifier": ["min"]},
                {"name": "genome_size", "modifier": ["max"]}
            ],
            fields=[{"name": "genome_size", "modifier": ["median"]}]
        )
        print(f"  Artifact ID: {result6['artifact_id']}")
        data6 = retrieve(result6['artifact_id'])
        print(f"  Fields (merged modifiers): {data6['fields']}")
        print("  Expected: min, max, median all in one field")

        # Test 7: Existence check
        print("\n[Test 7] Existence check")
        result7 = await process_attributes(
            user_query="Records that have genome_size",
            attributes=[{"name": "genome_size", "operator": "exists"}],
            fields=[]
        )
        print(f"  Artifact ID: {result7['artifact_id']}")
        data7 = retrieve(result7['artifact_id'])
        print(f"  Attributes: {data7['attributes']}")

        # Test 8: Hash consistency
        print("\n[Test 8] Hash consistency")
        result8a = await process_attributes(
            user_query="Test",
            attributes=[{"name": "genome_size", "operator": "<", "value": "1000"}],
            fields=[]
        )
        result8b = await process_attributes(
            user_query="Test",
            attributes=[{"name": "genome_size", "operator": "<", "value": "1000"}],
            fields=[]
        )
        data8a = retrieve(result8a['artifact_id'])
        data8b = retrieve(result8b['artifact_id'])
        print(f"  Hash A: {data8a['unique_id'][:16]}...")
        print(f"  Hash B: {data8b['unique_id'][:16]}...")
        print(f"  Hashes match: {data8a['unique_id'] == data8b['unique_id']}")

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)

    asyncio.run(test_process_attributes())
    asyncio.run(test_process_attributes())
