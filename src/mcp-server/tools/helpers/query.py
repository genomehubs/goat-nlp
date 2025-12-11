from urllib.parse import quote

from ...logging_config import get_logger

logger = get_logger(__name__)

"""Query building utilities for GoaT MCP server."""


def convert_size_to_bytes(value: str | int | float) -> int | str:
    """Convert human-readable size formats (e.g., '3G', '500M') to bytes.

    Supports: G (gigabytes), M (megabytes), K (kilobytes), B (bytes)

    Args:
        value: Size string like "3G", "500M", "1K" or numeric value

    Returns:
        Integer byte count or original value if not a size format
    """
    if isinstance(value, (int, float)):
        return int(value)

    if not isinstance(value, str):
        return value

    value_upper = value.upper().strip()

    # Check for size suffixes
    multipliers = {"G": 1_000_000_000, "M": 1_000_000, "K": 1_000, "B": 1}

    for suffix, multiplier in multipliers.items():
        if value_upper.endswith(suffix):
            try:
                numeric_part = float(value_upper[:-1])
                return int(numeric_part * multiplier)
            except ValueError:
                return value  # If conversion fails, return original

    # No suffix found, try to parse as plain number
    try:
        return int(value)
    except ValueError:
        return value  # Return original if not a number


def build_query_string(
    taxa: list[str] | None = None,
    rank: str | None = None,
    attributes: list[dict] | None = None,
    assemblies: list[str] | None = None,
    samples: list[str] | None = None,
    taxon_filter_type: str = "children",
) -> str:
    """Build a GoaT query string from optional components.

    Args:
        taxon: Optional taxonomic scope
        rank: Optional rank filter
        attributes: Optional attribute filters
    """
    query_parts = []
    escaped_taxa = []

    for taxon in taxa or []:
        escaped_taxon = (
            taxon.replace('*', '%2A')
            .replace(":", "%3A")
            .replace(",", "%2C")
            .replace("[", "%5B")
            .replace("]", "%5D")
        )
        escaped_taxa.append(escaped_taxon)
    if escaped_taxa:
        taxon_filters = {
            "children": "tax_tree",
            "matching": "tax_name",
            "lineage": "tax_lineage",
        }
        query_parts.append(f"{taxon_filters.get(taxon_filter_type, 'tax_tree')}%28{'%2C'.join(escaped_taxa)}%29")

    if rank:
        query_parts.append(f"tax_rank%28{rank}%29")

    if attributes:
        if attr_string := format_attributes(attributes):
            # Remove leading %20AND%20
            query_parts.append(attr_string.replace("%20AND%20", "", 1))

    return "%20AND%20".join(query_parts) if query_parts else ""


def format_attributes(attributes: list[dict]) -> str:
    """Format a list of attribute filters into a GoaT query string."""
    formatted_attrs = []
    for attr in attributes:
        name = attr.get("name")
        operator = attr.get("operator", "=")
        value = attr.get("value")
        summary_modifier = attr.get("summary_modifier")

        if not name:
            continue

        if summary_modifier:
            name = f"{summary_modifier}%28{name}%29"

        if value is None:
            formatted_attrs.append(f"{name}")
            continue

        # Convert size formats (e.g., "3G" -> 3000000000) to bytes
        value_converted = convert_size_to_bytes(value)
        value_str = str(value_converted)

        formatted_attrs.append(f"{name}{quote(operator)}{value_str}")

    if formatted_attrs:
        return "%20AND%20" + "%20AND%20".join(formatted_attrs)
    return ""


def set_exclusions(attributes: list[dict] | None) -> str:
    """Determine exclusion filters based on attribute status.

    Args:
        attributes: List of attribute filters
    """
    exclude_statuses = {}

    if not attributes:
        return ""

    for attr in attributes:
        if "exclude" in attr:
            for status in attr["exclude"]:
                if f"exclude{status}" not in exclude_statuses:
                    exclude_statuses[f"exclude{status}"] = []
                exclude_statuses[f"exclude{status}"].append(attr["name"])

    exclusion_str = ""
    for key, values in exclude_statuses.items():
        for i, value in enumerate(list(set(values))):
            exclusion_str += f"&{key}%5B{i}%5D={value}"

    if exclusion_str:
        exclusion_str = f"&{exclusion_str}"

    return exclusion_str


def process_modifiers(attributes: list[dict] | None) -> list[dict]:
    """Process modifiers into exclusions and summary statistics.

    Converts status-based modifiers (missing, direct, ancestral, descendant, estimated)
    into exclusion filters, while keeping summary modifiers (min, max, median, length, optional)
    as a field in the attribute dict for use in query string formatting.

    Supports both single modifier (string) and multiple modifiers (list).
    Example: {"name": "genome_size", "modifier": ["min", "direct"]}

    Args:
        attributes: List of attribute filters with optional modifiers

    Returns:
        List of processed attributes with:
        - Status modifiers converted to exclude lists
        - Summary modifiers preserved in a "summary_modifier" field
    """
    if not attributes:
        return []

    processed_attrs = []

    for attr in attributes:
        modifier = attr.get("modifier")
        if not modifier:
            processed_attrs.append(attr)
            continue

        attr_copy = {k: v for k, v in attr.items() if k != "modifier"}

        # Handle both single modifier (string) and multiple (list)
        modifiers = [modifier] if isinstance(modifier, str) else modifier

        # Separate status modifiers from summary modifiers
        status_set = {"missing", "direct", "ancestral", "descendant", "estimated"}
        status_modifiers = [m for m in modifiers if m in status_set]
        summary_modifiers = [m for m in modifiers if m in {"min", "max", "median", "length", "optional"}]

        # Process status modifiers - convert first one to exclusion
        if status_modifiers:
            status_mod = status_modifiers[0]  # Use first status modifier
            if status_mod == "missing":
                attr_copy["exclude"] = ["Direct", "Descendant"]
            elif status_mod == "direct":
                attr_copy["exclude"] = ["Ancestral", "Descendant", "Estimated", "Missing"]
            elif status_mod == "ancestral":
                attr_copy["exclude"] = ["Direct", "Descendant", "Estimated", "Missing"]
            elif status_mod == "descendant":
                attr_copy["exclude"] = ["Direct", "Ancestral", "Estimated", "Missing"]
            elif status_mod == "estimated":
                attr_copy["exclude"] = ["Direct", "Ancestral", "Descendant"]
            if "exclude" in attr_copy and not isinstance(attr_copy["exclude"], list):
                attr_copy["exclude"] = list(attr_copy["exclude"])

        # Process summary modifiers - store first one
        if summary_modifiers:
            attr_copy["summary_modifier"] = summary_modifiers[0]  # Use first summary modifier

        processed_attrs.append(attr_copy)

    logger.debug(f"Processed attributes with modifiers: {processed_attrs}")

    return processed_attrs


def set_search_tips(attributes: list[dict] | None, fields: list[dict] | None, intent: str | None) -> str:
    """Generate search tips based on selected attributes.

    Args:
        attributes: List of attribute filters
        fields: List of attribute fields to return
        intent: Search intent (e.g., "count", "table", "histogram")

    Returns:
        String of search tips for the LLM
    """
    tips = []
    if not attributes:
        tips.append("No specific attributes selected. You can ask about various attributes available in GoaT.")

    if intent == "table" and not fields:
        tips.append(
            "You have requested a table of results but have not specified any fields to include. "
            "Consider selecting specific attributes to display in the table."
        )

    attr_names = {attr["name"]: attr for attr in attributes or []}
    field_names = {}
    if fields:
        field_names = {field["name"]: field for field in fields}
        for field in fields:
            field_name = field.get("name")
            if not field_name:
                continue
            field_modifier = field.get("modifier")
            if not field_modifier:
                continue
            status_set = {"missing", "direct", "ancestral", "descendant", "estimated"}
            field_modifiers = [field_modifier] if isinstance(field_modifier, str) else field_modifier
            status_modifiers = [
                m for m in field_modifiers if m in status_set
            ]
            if (
                status_modifiers
                and len(status_modifiers) == 1
                and (
                    field_name not in attr_names
                    or "modifier" not in attr_names[field_name]
                    or status_modifiers[0] not in attr_names[field_name].get("modifier", [])
                )
            ):
                tips.append(
                    f"You have selected the field '{field_name}' with modifier(s) {status_modifiers}. "
                    f"Consider adding a corresponding attribute filter to refine your search results."
                )
    if attr_names:
        if missing_fields := [
            attr["name"]
            for attr in attributes
            if "name" in attr and attr["name"] not in field_names
        ]:
            tips.append(
                f"The following attributes are selected but not included in the fields: {', '.join(missing_fields)}. "
                "Consider adding them to the fields list to see their values in the results."
            )

    tips.append(
        "When querying, consider using summary statistics like min, max, median, or length "
        "to refine your results. Also, be aware of attribute statuses such as missing, direct, "
        "ancestral, descendant, and estimated to filter your data effectively."
    )

    return "\n".join(tips)
