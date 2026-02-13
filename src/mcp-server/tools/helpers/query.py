"""Query building utilities for GenomeHubs MCP server."""

from urllib.parse import quote

from ...config import DATASTORE_NAME
from ...logging_config import get_logger

logger = get_logger(__name__)


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
    f"""Build a {DATASTORE_NAME} query string from optional components.

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
            .replace("!", "%21")
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

    if assemblies:
        escaped_assemblies = [
            assembly.replace('*', '%2A').replace(":", "%3A").replace("!", "%21") for assembly in assemblies
        ]
        query_parts.append(f"assembly_id%3D{'%2C'.join(escaped_assemblies)}")

    if samples:
        escaped_samples = [
            sample.replace('*', '%2A').replace(":", "%3A").replace("!", "%21") for sample in samples
        ]
        query_parts.append(f"sample_id%3D{'%2C'.join(escaped_samples)}")

    if attributes:
        if attr_string := format_attributes(attributes):
            # Remove leading %20AND%20
            query_parts.append(attr_string.replace("%20AND%20", "", 1))

    return "%20AND%20".join(query_parts) if query_parts else ""


async def build_search_params(
    search_index: str,
    taxa: list[str] | None = None,
    taxon_filter_type: str = "children",
    assemblies: list[str] | None = None,
    samples: list[str] | None = None,
    rank: str | None = None,
    attributes: list[dict] | None = None,
    fields: list[dict] | None = None,
    names: list[str] | None = None,
    ranks: list[str] | None = None,
) -> dict:
    """Build base search params as a dict from validated parameters.

    Does NOT include pagination (size/offset), sorting, or report-specific params.
    Returns a dict that can be extended with additional params before serialisation.

    Args:
        search_index: "taxon", "assembly", or "sample"
        taxa: List of taxon names/IDs
        taxon_filter_type: "children", "matching", or "lineage"
        assemblies: List of assembly accessions
        samples: List of sample accessions
        rank: Taxonomic rank
        attributes: List of attribute filter dicts
        fields: List of field dicts to return
        names: List of taxon name classes
        ranks: List of rank names to return

    Returns:
        Dict with keys: query_string, result, exclusions, fields, names, ranks
        Ready for additional report params or pagination/sorting.
    """
    # Build base query string
    query_string = build_query_string(taxa, rank, attributes, assemblies, samples, taxon_filter_type)
    exclusions = set_exclusions(attributes)

    # Start with core params
    params = {
        "result": search_index,
        "includeEstimates": "true",
        "taxonomy": "ncbi",
        "report": "sources",
    }

    # Add query if present
    if query_string:
        params["query"] = query_string

    # Add exclusions (note: exclusions are already URL-encoded in set_exclusions)
    if exclusions:
        params["_exclusions_raw"] = exclusions  # Mark for special handling during serialisation

    # Add fields
    if fields:
        parsed_fields = []
        for field in fields:
            name = field.get("name")
            if not name:
                continue
            parsed_fields.append(name)
            if "modifier" in field:
                parsed_fields.extend(
                    f"{name}:{mod}"
                    for mod in field.get("modifier", [])
                    if mod
                    in {
                        "min",
                        "max",
                        "mean",
                        "median",
                        "mode",
                        "length",
                        "direct",
                        "descendant",
                        "ancestral",
                        "missing",
                    }
                )
        if parsed_fields:
            params["fields"] = parsed_fields

    # Add names
    if names:
        params["names"] = names

    # Add ranks
    if ranks:
        params["ranks"] = ranks

    return params


def params_dict_to_url(base_url: str, params: dict) -> str:
    """Convert a params dict to a URL query string.

    Handles special cases like URL-encoded exclusions and list values.

    Args:
        base_url: Base URL (e.g., "https://api.genomehubs.org/v2/search")
        params: Dict of parameters with special handling for:
            - "_exclusions_raw": already URL-encoded exclusion string (not converted)
            - list values: converted to comma-separated
            - string values: URL-encoded

    Returns:
        Full URL with query string
    """
    query_parts = []

    for key, value in params.items():
        # Skip special internal keys
        if key == "_exclusions_raw":
            continue

        if value is None:
            continue

        # Handle list values (fields, names, ranks)
        if isinstance(value, list):
            # Use safe="%" to avoid double-encoding already-encoded values
            value_str = "%2C".join(quote(str(v), safe="%") for v in value)
        else:
            # Use safe="%" to avoid double-encoding already-encoded values (e.g., query strings)
            value_str = quote(str(value), safe="%")

        query_parts.append(f"{key}={value_str}")

    # Add exclusions if present (already URL-encoded)
    if "_exclusions_raw" in params:
        if exclusions := params["_exclusions_raw"]:
            # Remove leading "&" if present
            exclusions = exclusions.lstrip("&")
            query_parts.append(exclusions)

    url = base_url
    if query_parts:
        url += "?" + "&".join(query_parts)

    return url


def build_user_facing_url(api_url: str, web_base: str = "") -> str:
    """Convert an API URL to a user-facing web URL.

    Replaces /api/v2 with web base and converts endpoint if needed.

    Args:
        api_url: API URL from search
        web_base: Base URL for user-facing interface (default: remove /api/v2)

    Returns:
        User-facing URL
    """
    url = api_url.replace("/api/v2", web_base)

    return url.replace("count?", "search?")


def merge_params_dicts(base_params: dict, additional_params: dict) -> dict:
    """Merge additional params into base params dict.

    Handles:
    - Overwriting existing keys
    - Extending list values (for fields, names, ranks)
    - Preserving special keys like "_exclusions_raw"

    Args:
        base_params: Base parameters dict
        additional_params: Additional/override parameters

    Returns:
        Merged dict
    """
    merged = base_params.copy()

    for key, value in additional_params.items():
        if key in {"fields", "names", "ranks"}:
            # Extend lists instead of replacing
            if key in merged and isinstance(merged[key], list):
                existing = merged[key]
                new_values = value if isinstance(value, list) else [value]
                # Add only new values not already in the list
                merged[key] = existing + [v for v in new_values if v not in existing]
            else:
                merged[key] = value
        else:
            # Override other keys
            merged[key] = value

    return merged


def format_attributes(attributes: list[dict]) -> str:
    f"""Format a list of attribute filters into a {DATASTORE_NAME} query string."""
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
        if isinstance(value, str):
            value_converted = convert_size_to_bytes(value)
            value_str = str(value_converted)
        elif isinstance(value, list):
            value_str = "%2C".join(str(v) for v in value)
        else:
            value_str = str(value)

        formatted_attrs.append(f"{name}{quote(operator)}{value_str.replace(' ', '%20').replace("*", '%2A')}")

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
                attr_copy["exclude"] = ["Direct", "Missing"]
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
        tips.append(
            f"No specific attributes selected. You can ask about various attributes "
            f"available in {DATASTORE_NAME}."
        )

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
