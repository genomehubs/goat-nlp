import re
from typing import Any

from ..logging_config import get_logger
from .helpers.fetch import fetch_valid_types
from .utilities import fetch_valid_ranks

logger = get_logger(__name__)


async def get_valid_types(search_index: str = "taxon") -> dict[str, Any]:
    """Fetch valid attribute types from GoaT API.

    Args:
        search_index: Index type (default: taxon)
    """
    return await fetch_valid_types(search_index)


async def get_metadata_for_attribute(
    attribute: str, search_index: str = "taxon"
) -> str:
    """Get metadata for a specific attribute in GoaT.

    ONLY use this to get detailed information about a single attribute,
    such as its description, type, and possible values. If you are unsure if an attribute exists or
    which attributes to use for filtering, use get_attribute_selection_context().

    DO NOT use this tool to guess attribute names or validate multiple attributes at once.

    Args:
        attribute: Name of the attribute to get metadata for
        search_index: Index type (default: taxon)
    """
    fields = await fetch_valid_types(search_index) or {}
    if attribute in fields:
        return format_processed_attribute(process_attribute(fields[attribute]), "exact", 1, 1)

    return f"Attribute '{attribute}' not found."


def extract_modifiers_and_operators(attribute: dict[str, Any]) -> dict[str, Any]:
    """Extract modifiers from an attribute dict."""
    modifiers = ["missing"]
    operators = ["=", "!=", "exists", "missing"]
    mods = attribute.get("summary", [])
    if isinstance(mods, str):
        mods = [mods]
    for mod in mods:
        if mod == "primary":
            continue
        if mod == "enum":
            operators.extend(["<", ">", "<=", ">="])
            continue
        if mod == "list" and "enum" not in mods:
            modifiers.append("length")
            # operators.extend(["in", "not in"])
        else:
            modifiers.append(mod)
    if not attribute.get("processed_type", "").endswith("keyword"):
        operators.extend(["<", ">", "<=", ">="])
    traverse_direction = attribute.get("traverse_direction")
    if traverse_direction in {"up", "both", "down"}:
        if traverse_direction in {"up", "both"}:
            modifiers.append("descendant")
        elif traverse_direction in {"down", "both"}:
            modifiers.extend(("ancestral", "estimate"))
    return modifiers, operators


def process_attribute(attribute: dict[str, Any]) -> dict[str, Any]:
    """Process a single attribute dict to extract modifiers and operators."""
    modifiers, operators = extract_modifiers_and_operators(attribute)
    description = attribute.get("description", "No description available.")
    if long_description := attribute.get("long_description", ""):
        description += f" {long_description}"
    constraint = attribute.get("constraint", {})
    value_metadata = attribute.get("value_metadata", {})
    if value_metadata:
        entries = []
        for key, value in value_metadata.items():
            if desc := value.get("description"):
                # Remove any text in brackets from the description
                desc = re.sub(r"\s*\(.*?\)", "", desc)
                entries.append(f"  {key}: {desc.strip()}")
        value_metadata = entries
    return {
        "name": attribute.get("name", "unknown"),
        "description": description,
        "processed_type": attribute.get("processed_type", "unknown"),
        "display_group": attribute.get("display_group", ""),
        "unit": attribute.get("unit"),
        "possible_values": ", ".join(constraint.get("enum", [])),
        "minimum": constraint.get("min"),
        "maximum": constraint.get("max"),
        "value_metadata": value_metadata,
        # "translations": attribute.get("translate", {}),
        "valid_modifiers": ", ".join(modifiers),
        "valid_operators": ", ".join(operators),
    }


def format_processed_attribute(
        processed_attribute: dict[str, Any],
        match_type: str,
        match_index: int,
        match_count: int,
        ) -> str:
    """Format attribute dict into a readable string."""
    lines = [
        (f"Keyword match to {processed_attribute['name']} based on a {match_type} match "
         f"at index {match_index}, with {match_count} matching words:"),
        "",
        f"Name: {processed_attribute['name']}",
        "- Name Type: attribute",
        f"- Description: {processed_attribute['description']}",
        f"- Type: {processed_attribute['processed_type']}",
    ]
    if display_group := processed_attribute.get("display_group"):
        lines.append(f"- Display Group: {display_group}")
    if unit := processed_attribute.get("unit"):
        lines.append(f"- Unit: {unit}")
    if possible_values := processed_attribute.get("possible_values", ""):
        lines.append(f"- Possible Values: {possible_values}")
    if minimum := processed_attribute.get("minimum"):
        lines.append(f"- Minimum: {minimum}")
    if maximum := processed_attribute.get("maximum"):
        lines.append(f"- Maximum: {maximum}")
    if modifiers := processed_attribute.get("valid_modifiers", ""):
        lines.append(f"- Valid Modifiers: {modifiers}")
    if operators := processed_attribute.get("valid_operators", ""):
        lines.append(f"- Valid Operators: {operators}")
    if value_metadata := processed_attribute.get("value_metadata", []):
        lines.append("- Value Metadata:")
        lines.extend(iter(value_metadata))
    return "\n".join(lines)


def find_matches(
    keyword_lower: str,
    keyword_words: set[str],
    name_search_text: str,
) -> None:
    """Find matches for a keyword in attribute text."""
    match_type = None
    match_index = -1
    match_count = 0
    # Check for complete phrase match first (higher priority)
    if keyword_lower in name_search_text:
        match_type = "whole phrase"
        match_index = name_search_text.index(keyword_lower)
    # If no phrase match, check if any individual words match
    elif keyword_words and any(word in name_search_text for word in keyword_words if len(word) > 2):
        match_type = "individual word"
        match_index = min(
            (name_search_text.index(word) for word in keyword_words if word in name_search_text),
            default=-1
        )
    if match_type:
        match_count = sum(word in name_search_text for word in keyword_words)

    return match_type, match_index, match_count


async def _get_attribute_context_internal(
    keyword: str, search_index: str = "taxon"
) -> dict[str, Any]:
    """Internal function to get attribute selection context.

    This is called by both the resource and the tool.
    """

    # Split keyword into individual words for matching
    keyword_lower = keyword.lower()
    keyword_words = set(keyword_lower.replace("_", " ").split())

    fields = await fetch_valid_types(search_index)
    title_attributes = []
    value_attributes = []
    name_attributes = []
    rank_attributes = []
    attributes = []
    for name, field in fields.items():
        # Get searchable text fields
        processed_attribute = process_attribute(field)
        name_lower = name.lower()
        description = processed_attribute.get("description", "").lower()
        display_group = processed_attribute.get("display_group", "").lower()
        possible_values = processed_attribute.get("possible_values", "").lower()
        value_metadata = ", ".join(processed_attribute.get("value_metadata", [])).lower()

        # Create combined search text
        name_search_text = f"{name_lower} {display_group} {description}"
        value_search_text = f"{possible_values} {value_metadata}"

        name_match_type, name_match_index, name_match_count = find_matches(
            keyword_lower, keyword_words, name_search_text
        )
        if name_match_type:
            title_attributes.append(
                format_processed_attribute(processed_attribute, name_match_type,
                                           name_match_index, name_match_count)
            )
        value_match_type, value_match_index, value_match_count = find_matches(
            keyword_lower, keyword_words, value_search_text
        )
        if value_match_type:
            value_attributes.append(
                format_processed_attribute(processed_attribute, value_match_type,
                                           value_match_index, value_match_count)
            )

    # Also check valid names
    valid_names = {
        "scientific name": "scientific_name",
        "common name": "common_name",
        "synonym": "synonym",
        "tolid prefix": "tolid_prefix",
        "tolid": "tolid_prefix",
        "authority": "authority"}
    if keyword_lower.replace("_", " ") in valid_names:
        attr_info = [
            f"Name: {valid_names[keyword_lower.replace('_', ' ')]}\n"
            "Name Type: name"
        ]
        name_attributes.append("\n".join(attr_info))

    # Also check valid ranks
    valid_ranks = await fetch_valid_ranks()
    logger.info(f"Checking keyword '{keyword_lower}' against valid ranks: {valid_ranks}")
    if keyword_lower in (rank.lower() for rank in valid_ranks):
        attr_info = [f"Name: {keyword_lower}", "Name Type: rank"]
        rank_attributes.append("\n".join(attr_info))

    if not (title_attributes or value_attributes or name_attributes or rank_attributes):
        return f"""No attributes, names, or ranks found matching keyword '{keyword}'.

        Try different keywords or use a descriptive phrase to expand your search."""

    if name_attributes:
        attributes.extend(
            (
                "=== Name Matches ===",
                "These can be used as name columns in GoaT tables.",
                "The following name matches your keyword:",
            )
        )
        attributes.extend(name_attributes)
    if rank_attributes:
        attributes.extend(
            (
                "=== Rank Matches ===",
                "These can be used as rank columns in GoaT tables.",
                "The following rank matches your keyword:",
            )
        )
        attributes.extend(rank_attributes)
    if title_attributes:
        title_len = len(title_attributes)
        title_count = f" {title_len}" if title_len > 1 else ""
        plural = "s" if title_len > 1 else ""
        match_plural = "" if title_len > 1 else "es"
        attributes.extend(
            (
                "=== Attribute Matches ===",
                "These can be used as attribute filters or fields in GoaT queries.",
                f"The following{title_count} attribute{plural} match{match_plural} your keyword:",
            )
        )
        attributes.extend(title_attributes)
    if value_attributes:
        value_len = len(value_attributes)
        value_count = f" {value_len}" if value_len > 1 else ""
        plural = "s" if value_len > 1 else ""
        match_plural = "" if value_len > 1 else "es"
        has_plural = "have" if value_len > 1 else "has a"
        attributes.extend(
            (
                "=== Attribute value Matches ===",
                "The keyword you provided matches possible values to be passed to these attribute "
                "filters in GoaT queries.",
                (f"The following{value_count} attribute{plural} {has_plural} value{plural} "
                 f"that match{match_plural} your keyword:"),
            )
        )
        attributes.extend(value_attributes)

    taxon_note = ""
    if search_index == "taxon":
        taxon_note = (
            "Note: If a user wants to know 'which species have ...', the LLM should choose an attribute "
            "that DOES NOT support an \"ancestral\" modifier, if available, to avoid including ancestral data "
            "in the results. Example: 'which species have assemblies?' -> use 'assembly_level' instead of "
            "'assembly_span'.\n"
        )

    return f"""GoaT Attribute Selection Context:

Choose from the following attributes, names, and ranks to filter GoaT data based on your query.

The following attributes, names, and ranks match the keyword '{keyword}':
{taxon_note}
{"\n".join(attributes)}
"""


async def get_attribute_selection_context(
    keyword: str,
    comparison: str | None = None,
    search_index: str = "taxon"
) -> str:
    """Get context information for attribute selection.

    An LLM MUST use this to choose appropriate attributes to filter by
    based on a user query. The LLM MUST always check whether an attribute
    exists before using it in a query.

    The LLM must check the returned 'Name type' for each attribute to
    determine whether it is an 'attribute', a 'name', or a 'rank'.

    THE LLM MUST NOT make assumptions about attribute names or types
    without checking this tool first.

    THE LLM MUST use the information provided for each attribute
    to understand how to use it correctly in a query.

    IMPORTANT: If you do not get results with a keyword search, try different
    keywords or use a descriptive phrase to expand your search.


    IMPORTANT: If the user wants to know about chromosome count, it is better to also
    return chromosome number as this is more likely to be the required field.

    IMPORTANT: for questions about a project, bioproject is only the correct attribute
    if the user specifically mentions bioproject or if the value begins with "PRJ".

    Args:
        keyword: Keyword or phrase  to guide attribute selection
        comparison: Comparison context to guide attribute selection
        search_index: Index type (default: taxon)
    """
    logger.info(f"get_attribute_selection_context called: keyword='{keyword}', "
                f"comparison='{comparison}', search_index={search_index}")

    return await _get_attribute_context_internal(keyword, search_index)


def register_tools(mcp) -> None:
    """Register GoaT attribute tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    # mcp.tool()(get_valid_types)
    mcp.tool()(get_metadata_for_attribute)
    mcp.tool()(get_attribute_selection_context)
