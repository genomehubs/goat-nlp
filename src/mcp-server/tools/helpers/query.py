from urllib.parse import quote

"""Query building utilities for GoaT MCP server."""


def build_query_string(
    taxon: str | None = None,
    rank: str | None = None,
    attributes: list[dict] | None = None,
) -> str:
    """Build a GoaT query string from optional components.

    Args:
        taxon: Optional taxonomic scope
        rank: Optional rank filter
        attributes: Optional attribute filters
    """
    query_parts = []

    if taxon:
        escaped_taxon = (
            taxon.replace('*', '%2A')
            .replace(":", "%3A")
            .replace(",", "%2C")
            .replace("[", "%5B")
            .replace("]", "%5D")
        )
        query_parts.append(f"tax_tree%28{escaped_taxon}%29")

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

        if not name:
            continue

        if value is None:
            formatted_attrs.append(f"{name}")
            continue
        value_str = str(value)

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
        for i, value in enumerate(values):
            exclusion_str += f"&{key}%5B{i}%5D={value}"

    if exclusion_str:
        exclusion_str = f"&{exclusion_str}"

    return exclusion_str
