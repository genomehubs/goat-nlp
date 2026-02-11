"""Formatting utilities for GenomeHubs MCP server."""

from ...config import DATASTORE_FULL_DESCRIPTION, DATASTORE_NAME
from ...logging_config import get_logger

logger = get_logger(__name__)


def rank_description(rank: str) -> str:
    """Return a human-readable description for a given taxonomic rank."""
    return {
        "subspecies": "subspecies",
        "species": "species",
        "genus": "genera",
        "family": "families",
        "order": "orders",
        "class": "classes",
        "phylum": "phyla",
        "kingdom": "kingdoms",
        "domain": "domains",
    }.get(rank, f"{rank} level taxa")


def format_count(result: dict, taxa: list[str] | None = None, rank: str = "", url: str = "") -> str:
    f"""Format count into a readable string with {DATASTORE_NAME} context."""
    count = result.get("count", 0)

    search_url = url.replace("/api/v2", "")
    search_url = (
        search_url.replace("count?", "search?") + "&size=10&report=sources"
    )
    return f"""
According to {DATASTORE_FULL_DESCRIPTION}, there are {count} {rank_description(rank)} \
within {', '.join(taxa) if taxa else "all taxa"}.

This count is based on taxa with sequence data from the NCBI taxonomy,
supplemented by additional metadata from the {DATASTORE_NAME} database.

Explore these results in the {DATASTORE_NAME} web interface:
{search_url}
"""


def format_lineage(lineage: list[dict]) -> str:
    """Format a taxonomic lineage into a readable string."""
    lineage_parts = []
    for taxon in reversed(lineage):
        name = taxon.get("scientific_name", "Unknown")
        rank = taxon.get("taxon_rank")
        anc_str = name
        if rank is not None:
            anc_str += f" ({rank})"
        lineage_parts.append(anc_str)
    return " > ".join(lineage_parts)


def format_attribute_value(name: str, attribute: dict, truncate: bool = True) -> str:
    """Format a single attribute value into a readable string."""
    value = attribute.get("value")
    summary = attribute.get("summary")
    min_value = attribute.get("min")
    max_value = attribute.get("max")
    aggregation_source = attribute.get("aggregation_source")
    if isinstance(value, list):
        attr_len = len(value)
        if truncate and attr_len > 10:
            last_item = value[-1] if attr_len > 0 else ""
            value = ", ".join(str(v) for v in value[:10])  # Limit to first 10 values
            more = attr_len - 10
            value += f", {last_item}" if (more == 1) else f", ... ({more} more)"
        else:
            value = ", ".join(str(v) for v in value)
    attr_str = f"{name}: {value}"
    if summary is not None:
        attr_str += f" (Summary: {summary})"
    if min_value is not None and max_value is not None and min_value != max_value:
        attr_str += f" (Range: {min_value}-{max_value})"
    if aggregation_source is not None:
        attr_str += f" (Source: {aggregation_source})"
    return attr_str


def format_record(record: dict, url: str, attributes: list[str] | None = None, truncate: bool = True) -> str:
    f"""Format a {DATASTORE_NAME} record into a readable string."""
    lineage_str = format_lineage(record.get("lineage", []))

    lines = [
        f"Scientific Name: {record.get('scientific_name', 'Unknown')}",
        f"Taxon ID: {record.get('taxon_id', 'Unknown')}",
        f"Rank: {record.get('taxon_rank', 'Unknown')}",
        f"{DATASTORE_NAME} URL: {url.replace('/api/v2', '')}",
        f"Lineage: {lineage_str}"
    ]

    for attr_name, attr in record.get("attributes", {}).items():
        if attributes is None or attr_name in attributes:
            lines.append(format_attribute_value(attr_name, attr, truncate=truncate))
    return "\n".join(lines)


def format_result_table(
    results: list[dict],
    search_fields: list[str],
    search_names: list[str],
    search_ranks: list[str],
    search_url: str,
) -> str:
    f"""Format search results as a markdown table with context.

    Args:
        results: List of result records
        search_fields: List of fields to include in the table
        search_names: List of taxon name classes to include
        search_ranks: List of taxonomic ranks to include
        search_url: {DATASTORE_NAME} web interface URL

    Returns:
        Formatted markdown string with summary and table
    """
    if not results:
        return f"No results found.\n\nExplore in {DATASTORE_NAME}: {search_url}"

    columns = []

    # Build rows
    rows = []
    flags = 0
    for result in results:
        record = result.get("result", {})
        row_values = []
        if not columns:
            # Determine columns from first record
            columns.extend(key for key in record.keys() if key.endswith("_id"))
            if record.get("scientific_name") is not None:
                columns.append("scientific_name")
            if record.get("taxon_rank") is not None:
                columns.append("taxon_rank")
            if "fields" in record:
                columns.extend(record["fields"].keys())
            if search_fields:
                # Ensure requested fields are included
                for field in search_fields:
                    field_name = field.get("name")
                    if field_name is None:
                        continue
                    if field_name not in columns:
                        columns.append(field_name)
                    if modifiers := field.get("modifier", []):
                        for mod in modifiers:
                            full_field = f"{field_name}:{mod}"
                            if full_field not in columns:
                                columns.append(full_field)
            if search_names:
                columns.extend(iter(search_names))
            if search_ranks:
                columns.extend(iter(search_ranks))
            # Build header
            header = "| " + " | ".join(columns) + " |"
            separator = "| " + " | ".join(["---"] * len(columns)) + " |"

        fields = record.get("fields", {})
        names = record.get("names", {})
        ranks = record.get("ranks", {})
        for col in columns:
            flag = False
            # Handle different field types
            if record.get(col) is not None:
                value = record.get(col)
            elif col in fields and fields[col] is not None:
                attr_value = fields[col].get("value", "N/A")
                if "ancestor" in fields[col].get("aggregation_source", []):
                    flag = True
                    flags += 1
                # Format lists concisely
                if isinstance(attr_value, list):
                    value = (
                        f"{', '.join(str(v) for v in attr_value[:3])}... (+{len(attr_value) - 3})"
                        if len(attr_value) > 3
                        else ", ".join(str(v) for v in attr_value)
                    )
                else:
                    value = str(attr_value)
            elif col in search_names:
                value = ", ".join(names.get(col, {}).get("name", ["N/A"]))
            elif col in search_ranks:
                value = ranks.get(col, {}).get("scientific_name", "N/A")
            else:
                value = "N/A"

            # Truncate long values
            if len(str(value)) > 50:
                value = f"{str(value)[:47]}..."

            if flag:
                value = f"{value} (Ancestral)"

            row_values.append(str(value))

        rows.append("| " + " | ".join(row_values) + " |")

    # Assemble table
    table = "\n".join([header, separator] + rows)
    flag_note = (
        "\n\n(Note: Values marked with '(Ancestral)' are inferred from ancestral data.)"
        if flags > 0
        else ""
    )
    return f"""Here are the top results:
{table}{flag_note}
"""


def format_sources_report(report_data: dict, search_url: str) -> str:
    f"""Format a sources report for LLM interpretation and user presentation.

    Args:
        report_data: The sources report from {DATASTORE_NAME} API

    Returns:
        Formatted markdown string with source attribution
    """
    if not report_data or "report" not in report_data:
        return "No source information available."

    sources = report_data.get("report", {}).get("report", {}).get("sources", {})

    if not sources:
        return "No source information available."

    lines = ["## Sources\n"]

    for source_name, source_data in sources.items():
        # Extract basic fields
        count = source_data.get("record_count", 0)
        attributes = source_data.get("attributes", [])
        url = source_data.get("source_url", "")
        date = source_data.get("date_accessed", "")

        lines.extend((f"### {source_name}", f"**Records contributed:** {count:,}"))
        # Attributes provided
        if attributes:
            attr_list = ", ".join(f"`{attr}`" for attr in attributes)
            lines.append(f"**Attributes:** {attr_list}")

        # URL and date
        if url:
            lines.append(f"**URL:** {url}")
        if date:
            lines.append(f"**Last updated:** {date}")

        lines.append("")  # Empty line between sources

    result = "\n".join(lines)
    return f"""{result}

{DATASTORE_NAME} URL: {search_url}"""


def format_histogram_report(report_data: dict, url: str, logger_instance=None) -> str:
    f"""Format a histogram report for LLM interpretation and user presentation.

    Args:
        report_data: The histogram report from {DATASTORE_NAME} API
        logger_instance: Optional logger instance for debugging

    Returns:
        Formatted markdown string with histogram summary and distribution
    """
    if logger_instance is None:
        logger_instance = logger

    if not report_data or "report" not in report_data:
        logger_instance.warning("Histogram report missing 'report' key or empty.")
        return "No histogram information available."

    # Accept either full API response or nested 'report' object
    histogram_data = {}
    if isinstance(report_data, dict):
        histogram_data = report_data.get("report", {}).get("report", {}).get("histogram", {})
    if not histogram_data:
        logger_instance.warning("Histogram report missing 'histogram' key or empty.")
        return "No histogram information available."

    # In current API, structure is:
    # histogram_data: { field, scale, stats, query, x, histograms: { buckets, allValues, ... } }
    histograms = histogram_data.get("histograms", {})
    if not histograms:
        logger_instance.warning("Histogram report missing 'histograms' sub-object.")

    # Extract key information from the correct levels
    field = histogram_data.get("field", "unknown")
    scale = histogram_data.get("scale", "linear")
    query = histogram_data.get("query", "")
    total_count = histogram_data.get("x", 0)
    stats = histogram_data.get("stats", {})
    buckets = histograms.get("buckets", [])
    counts = histograms.get("allValues", [])

    # Determine index label for totals
    result_index = (
        histogram_data.get("xQuery", {}).get("result")
        or report_data.get("report", {}).get("report", {}).get("histogram", {}).get("xQuery", {}).get("result")
    )
    total_label = {
        "taxon": "Total species",
        "assembly": "Total assemblies",
        "sample": "Total samples",
    }.get(result_index, "Total records")

    # Build the summary
    lines = [
        "## Histogram Summary",
        f"- **{total_label}**: {total_count}",
        f"- **Field**: `{field}`",
        f"- **Scale**: {scale}",
        f"- **Query**: `{query}`",
        "",
        "### Statistics",
    ]

    # Add statistics if available
    if stats:
        try:
            format_stats_and_buckets(stats, lines, buckets, counts)
        except Exception as e:
            logger_instance.error(f"Error formatting stats and buckets: {e}")
            format_buckets(lines, buckets, counts)
    else:
        format_buckets(lines, buckets, counts)
    result = "\n".join(lines)
    return f"""{result}

{DATASTORE_NAME} URL: {url}"""


def format_stats_and_buckets(stats, lines, buckets, counts):
    min_val = stats.get("min", 0)
    max_val = stats.get("max", 0)
    avg_val = stats.get("avg", 0)
    sum_val = stats.get("sum", 0)

    lines.extend([
        f"- **Min**: {min_val:,}",
        f"- **Max**: {max_val:,}",
        f"- **Average**: {avg_val:,.2f}",
        f"- **Sum**: {sum_val:,}",
        "",
    ])

    # Build distribution table
    if buckets and counts and len(buckets) > 1:
        lines.extend([
            "### Distribution (bucket ranges and counts)",
            "",
            "| Bucket Min | Bucket Max | Count |",
            "|-------------------:|-------------------:|------:|",
        ])

        # Create rows for each bucket
        for i in range(len(buckets) - 1):
            bucket_min = buckets[i]
            bucket_max = buckets[i + 1]
            count = counts[i] if i < len(counts) else 0

            lines.append(f"| {bucket_min:,.0f} | {bucket_max:,.0f} | {count} |")


def format_buckets(lines, buckets, counts):
    lines.extend([
        "### Distribution (value counts)",
        "",
        "| Value | Count |",
        "|------:|------:|",
    ])
    for i, count in enumerate(counts):
        value = buckets[i] if i < len(buckets) else "N/A"
        lines.append(f"| {value} | {count} |")
    lines.append("")
