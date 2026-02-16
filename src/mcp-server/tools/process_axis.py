"""Process axis tool for preparing simple axis definitions for report visualisations."""

from typing import Any

from ..config import DATASTORE_NAME
from ..logging_config import get_logger
from .helpers.constants import FIELD_CACHE
from .helpers.errors import invalid_attribute_error, invalid_option_error, parsing_error
from .helpers.fetch import fetch_valid_types
from .helpers.processor_common import finalise_and_store
from .helpers.validation import validate_attribute_name
from .utilities import fetch_valid_ranks

logger = get_logger(__name__)

PROCESS_AXIS_PROMPT = (
    f"""Process and validate simple axis definitions for {DATASTORE_NAME} report visualisations.

This tool handles SIMPLE axis definitions: field names, ranks, or fields with modifiers.
For COMPLEX axes (with operators, value filters, or identifier constraints), use process_axis_complex() instead.

If successful, this tool returns an artifact token that can be passed to get_report().

WHEN TO USE THIS TOOL:
- Axis is a field name: "genome_size", "assembly_level"
- Axis is a rank name: "phylum", "genus", "family"
- Axis is a field with modifiers: "minimum genome_size", "directly measured chromosome_number"

WHEN TO USE process_axis_complex() INSTEAD:
- Axis has operators/filters: "genome_size > 3G", "assembly_level = chromosome"
- Axis has identifier constraints: "for Mammalia", "excluding Felis"
- Axis has complex attribute combinations

FOLLOW THESE STEPS EXACTLY:

1. **axis_name**: Which axis this definition applies to
   Options: "x", "y", "z", or "category"
   Examples:
   - Histogram x-axis: axis_name="x"
   - Scatter plot axes: axis_name="x" (first call), axis_name="y" (second call)
   - Tree data bars: axis_name="y"
   - Grouping/category: axis_name="category"

2. **axis_definition**: The field or rank name, optionally with modifiers
   Format: "[modifier] field_name" or "rank_name"
   Examples:
   - Simple field: "genome_size"
   - With modifier: "minimum genome_size", "median chromosome_number"
   - Multiple modifiers: "minimum directly measured genome_size"
   - Rank: "phylum", "genus", "family"

   VALID MODIFIERS:
   - Summary: min, max, median, mean, sum, list
   - Status: direct, ancestral, descendant, estimated, missing

3. **bin_count**: Number of bins/categories to display (optional)
   - For numeric axes: groups values into N bins (e.g., 20 bins for genome size)
   - For category axes: limits display to top N categories (e.g., 10 most common phyla)
   - For keyword axes: limits results to N groups
   Examples: 10, 20, 50
   If not specified, API will choose appropriate default.
   APPLIES TO: histogram (x-axis), scatter (x/y axes), category grouping

4. **show_other**: Whether to include an "Other" bin/category for low-frequency groups (optional, default: False)
   Example: show_other=True
   APPLIES TO: category axes and keyword axes in histogram and scatter reports.

5. **scale**: Scale type for numeric/keyword axes (optional)
   Options: "linear" (default), "sqrt", "log", "log2", "log10"
   Examples:
   - Linear scale: scale="linear" or omit
   - Log scale: scale="log"
   - Sqrt scale: scale="sqrt"
   APPLIES TO: numeric and keyword-based axes in histogram, scatter, and tree reports.
   NOT applicable for pure category/rank axes.

6. **min_value**: Minimum value for numeric/keyword axis range (optional)
   Example: min_value=1000000 (1Mb for genome_size)
   APPLIES TO: numeric and keyword-based axes in histogram and scatter reports.
   NOT applicable for category/rank axes.

7. **max_value**: Maximum value for numeric/keyword axis range (optional)
   Example: max_value=10000000000 (10Gb for genome_size)
   APPLIES TO: numeric and keyword-based axes in histogram and scatter reports.
   NOT applicable for category/rank axes.

8. **user_query**: Copy the original question EXACTLY. DO NOT MODIFY IT.

EXAMPLES:

Example 1: Simple histogram
Query: "What is the distribution of genome sizes?"
→ process_axis(
    axis_name="x",
    axis_definition="genome_size",
    user_query="What is the distribution of genome sizes?"
  )

Example 2: Histogram with modifiers and options
Query: "Show minimum genome_size distribution with 20 bins on log scale"
→ process_axis(
    axis_name="x",
    axis_definition="minimum genome_size",
    bin_count=20,
    scale="log",
    user_query="Show minimum genome_size distribution with 20 bins on log scale"
  )

Example 3: Scatter plot (two calls)
Query: "How do genome size and chromosome number compare?"
→ Call 1: process_axis(axis_name="x", axis_definition="genome_size", ...)
→ Call 2: process_axis(axis_name="y", axis_definition="chromosome_number", ...)

Example 4: Grouped by rank
Query: "Histogram of genome sizes grouped by phylum"
→ Call 1: process_axis(axis_name="x", axis_definition="genome_size", ...)
→ Call 2: process_axis(axis_name="category", axis_definition="phylum", ...)

Example 5: Tree with data bars
Query: "Show taxonomy tree with genome sizes at leaves"
→ process_axis(axis_name="y", axis_definition="genome_size", ...)

DO NOT CALL unless you've completed all steps above!
If the axis has operators or filters, use process_axis_complex() instead!
"""
)


async def process_axis(
    axis_name: str,
    axis_definition: str,
    user_query: str,
    bin_count: int | None = None,
    show_other: bool = False,
    scale: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    search_index: str = "taxon",
) -> dict[str, Any]:
    f"""Process and validate a simple axis definition.

    Args:
        axis_name: Which axis this applies to ("x", "y", "z", or "category")
        axis_definition: Field or rank name, optionally with modifiers (e.g., "minimum genome_size")
        user_query: The original user question
        bin_count: Optional number of bins/categories (for all axis types: numeric, category, keyword)
        show_other: Whether to include an "Other" category for low-frequency groups (optional, default: False)
        scale: Optional scale type ("linear", "sqrt", "log", "log2", "log10") - numeric/keyword axes only
        min_value: Optional minimum value for axis range - numeric/keyword axes only
        max_value: Optional maximum value for axis range - numeric/keyword axes only
        search_index: The search index to use ("taxon", "assembly", or "sample")

    Returns:
        A dictionary with processed axis definition for {DATASTORE_NAME} API queries.
    """
    # Validate axis_name
    valid_axis_names = {"x", "y", "z", "category"}
    if axis_name not in valid_axis_names:
        raise ValueError(invalid_option_error("axis_name", axis_name, valid_axis_names))

    # Validate scale if provided
    if scale:
        valid_scales = {"linear", "sqrt", "log", "log2", "log10"}
        if scale not in valid_scales:
            raise ValueError(invalid_option_error("scale", scale, valid_scales))

    # Parse axis_definition to extract field/rank and modifiers
    # Format: "[modifier...] field_name"
    parts = axis_definition.strip().split()

    # Known modifiers
    valid_modifiers = {
        "min", "minimum",
        "max", "maximum",
        "median", "mean", "sum", "list",
        "direct", "directly",
        "ancestral", "descendant", "estimated", "missing"
    }

    modifiers = []
    field_or_rank = None

    # Extract modifiers from the start
    for part in parts:
        part_lower = part.lower()
        if part_lower in valid_modifiers:
            # Normalise modifier names
            if part_lower == "minimum":
                modifiers.append("min")
            elif part_lower == "maximum":
                modifiers.append("max")
            elif part_lower == "directly":
                modifiers.append("direct")
            else:
                modifiers.append(part_lower)
        else:
            # First non-modifier word is the field/rank
            # Join remaining parts in case field name has underscores that got split
            field_or_rank = "_".join(parts[parts.index(part):])
            break

    if not field_or_rank:
        raise ValueError(parsing_error("axis_definition", axis_definition, "[modifier...] field_name"))

    # Check if it's a rank or a field
    valid_ranks = await fetch_valid_ranks()
    is_rank = field_or_rank in valid_ranks

    if not is_rank:
        # Validate as a field
        await fetch_valid_types(search_index)
        try:
            validate_attribute_name(field_or_rank, search_index, FIELD_CACHE)
        except ValueError as e:
            valid_ranks = await fetch_valid_ranks()
            raise ValueError(
                invalid_attribute_error(field_or_rank, "field or rank", valid_ranks)
            ) from e

    if show_other:
        bin_count = f"{bin_count or 5}+"

    # Build the result
    result: dict[str, Any] = {
        "axis_name": axis_name,
        "field_or_rank": field_or_rank,
        "is_rank": is_rank,
        "modifiers": modifiers,
        "bin_count": bin_count,
        "show_other": show_other,
        "scale": scale,
        "min_value": min_value,
        "max_value": max_value,
        "user_query": user_query,
    }

    return finalise_and_store(result)


process_axis.__doc__ = PROCESS_AXIS_PROMPT


def register_tools(mcp) -> None:
    """Register process axis tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(process_axis)


if __name__ == "__main__":
    import asyncio

    from .artifact_store import retrieve

    async def test_process_axis():
        """Test examples for process_axis."""
        print("=" * 60)
        print("Testing process_axis")
        print("=" * 60)

        # Test 1: Simple field
        print("\n[Test 1] Simple field (genome_size)")
        result1 = await process_axis(
            axis_name="x",
            axis_definition="genome_size",
            user_query="What is the distribution of genome sizes?"
        )
        print(f"  Artifact ID: {result1['artifact_id']}")
        data1 = retrieve(result1['artifact_id'])
        print(f"  Field/Rank: {data1['field_or_rank']}")
        print(f"  Is Rank: {data1['is_rank']}")
        print(f"  Modifiers: {data1['modifiers']}")

        # Test 2: Field with single modifier
        print("\n[Test 2] Field with single modifier (minimum genome_size)")
        result2 = await process_axis(
            axis_name="x",
            axis_definition="minimum genome_size",
            user_query="Show minimum genome sizes"
        )
        print(f"  Artifact ID: {result2['artifact_id']}")
        data2 = retrieve(result2['artifact_id'])
        print(f"  Field/Rank: {data2['field_or_rank']}")
        print(f"  Modifiers: {data2['modifiers']}")

        # Test 3: Rank (category)
        print("\n[Test 3] Rank as category (phylum)")
        result3 = await process_axis(
            axis_name="category",
            axis_definition="phylum",
            user_query="Group by phylum"
        )
        print(f"  Artifact ID: {result3['artifact_id']}")
        data3 = retrieve(result3['artifact_id'])
        print(f"  Field/Rank: {data3['field_or_rank']}")
        print(f"  Is Rank: {data3['is_rank']}")
        print(f"  Modifiers: {data3['modifiers']}")

        # Test 4: With options (bin_count, scale)
        print("\n[Test 4] With options (bin_count=20, scale=log)")
        result4 = await process_axis(
            axis_name="x",
            axis_definition="genome_size",
            bin_count=20,
            scale="log",
            user_query="Distribution with 20 bins on log scale"
        )
        print(f"  Artifact ID: {result4['artifact_id']}")
        data4 = retrieve(result4['artifact_id'])
        print(f"  Field/Rank: {data4['field_or_rank']}")
        print(f"  Bin count: {data4['bin_count']}")
        print(f"  Scale: {data4['scale']}")

        # Test 5: With min/max range
        print("\n[Test 5] With min/max range")
        result5 = await process_axis(
            axis_name="x",
            axis_definition="genome_size",
            min_value=1000000,
            max_value=10000000000,
            user_query="Genome sizes between 1Mb and 10Gb"
        )
        print(f"  Artifact ID: {result5['artifact_id']}")
        data5 = retrieve(result5['artifact_id'])
        print(f"  Min value: {data5['min_value']}")
        print(f"  Max value: {data5['max_value']}")

        # Test 6: Y-axis for scatter
        print("\n[Test 6] Y-axis for scatter plot")
        result6 = await process_axis(
            axis_name="y",
            axis_definition="chromosome_number",
            user_query="Compare genome size and chromosome number"
        )
        print(f"  Artifact ID: {result6['artifact_id']}")
        data6 = retrieve(result6['artifact_id'])
        print(f"  Axis name: {data6['axis_name']}")
        print(f"  Field/Rank: {data6['field_or_rank']}")

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)

    asyncio.run(test_process_axis())
