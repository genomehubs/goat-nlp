from ..config import DATASTORE_NAME
from ..logging_config import get_logger
from .helpers.api import make_api_request
from .helpers.constants import FIELD_CACHE
from .helpers.fetch import fetch_valid_types
from .helpers.formatting import format_histogram_report, format_sources_report
from .helpers.urls import update_query_string
from .helpers.validation import validate_attribute_name
from .utilities import fetch_valid_ranks

logger = get_logger(__name__)


async def get_report(
    search_url: str,
    report_type: str = "sources",
    rank: str | None = None,
    x_field: str | None = None,
    y_field: str | None = None,
) -> str:
    f"""Get a detailed report from {DATASTORE_NAME} based on a search URL.

    This tool generates various types of analytical reports from a {DATASTORE_NAME} search.
    It works with the search_url returned from a previous submit_query call.

    IMPORTANT FOR HISTOGRAMS: To generate a histogram for a specific attribute,
    use the x_field parameter to specify which attribute to plot. The LLM can
    choose ANY valid attribute for the search_index, even if it wasn't included
    in the original search query.

    Example workflow for "chromosome number distribution for flowering plants":
    1. Call submit_query(taxa=["Angiospermae"], rank="species") to get search_url
    2. Call get_report(search_url=<url>, report_type="histogram",
                           rank="species", x_field="chromosome_number")

    The x_field parameter tells {DATASTORE_NAME} which attribute to use for the histogram,
    this should be part of the original search the original search.

    Report types include:
    - sources: List of data sources contributing to the results
    - histogram: Distribution of values for a specific attribute (use x_field)
    - scatter: Scatter plot comparing two attributes (use x_field and y_field)
    - tree: Taxonomic tree representation

    Args:
        search_url: Full {DATASTORE_NAME} search URL from a previous submit_query call.
                    CRITICAL: this must be the exact URL returned by submit_query,
                    without any manual modifications.
        report_type: Type of report to generate (default: sources)
        rank: Taxonomic rank filter (REQUIRED for histogram/scatter on taxon index)
        x_field: Attribute name for histogram x-axis or scatter plot x-axis
                 (e.g., "chromosome_number", "assembly_span", "genome_size")
        y_field: Attribute name for scatter plot y-axis
    """
    logger.info(f"get_report called: search_url={search_url}, report_type={report_type}, "
                f"rank={rank}, x_field={x_field}, y_field={y_field}")

    # Validate and normalize URL encoding
    # Import urllib for proper URL handling
    from urllib.parse import quote, urlencode, urlparse, urlunparse

    # Check if URL needs re-encoding (has unescaped characters)
    parsed = urlparse(search_url)
    if parsed.query and any(char in parsed.query for char in ['(', ')', ' ']):
        logger.warning(f"URL contains unescaped characters, re-encoding: {search_url}")
        # Re-encode only the unescaped characters, preserving already-encoded ones
        query_params = {}
        for pair in parsed.query.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                # Only encode if not already encoded (safe= preserves % for already-encoded chars)
                query_params[key] = quote(value, safe='%')

        # Rebuild URL with properly encoded query
        search_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                parsed.params, urlencode(query_params, safe='%'),
                                parsed.fragment))
        logger.info(f"Re-encoded URL: {search_url}")

    url = (
        search_url.replace("/api/v2/", "/")
        .replace("/search", "/api/v2/report")
        .replace("/count", "/api/v2/report")
    )
    search_index = url.split("result=")[1].split("&")[0]
    logger.info(f"Extracted search_index: {search_index}")
    url = update_query_string(url, "report", report_type)
    need_rank = {"histogram", "scatter"} if "result=taxon" in url else set()
    if need_rank and report_type in need_rank:
        if not rank and "tax_rank%28" in url:
            rank = url.split("tax_rank%28")[1].split("%29")[0]
            logger.info(f"Extracted rank from URL: {rank}")
        if not rank:
            return (
                f"Error: When querying {report_type} reports for the "
                f"taxon index, a 'rank' parameter must be provided."
            )
        valid_ranks = await fetch_valid_ranks()
        if rank not in valid_ranks:
            return (f"Error: Invalid rank '{rank}' provided for {DATASTORE_NAME} taxa reports."
                    f" Valid ranks are: {', '.join(valid_ranks)}.")

        url = update_query_string(url, "rank", rank)

    # Populate FIELD_CACHE before validation
    await fetch_valid_types(search_index)

    try:
        if x_field:
            x_field = validate_attribute_name(x_field, search_index, FIELD_CACHE)
            if f"query={x_field}%20AND" not in url and f"query={x_field}&" not in url:
                url = url.replace("query=", f"query={x_field}%20AND%20")
        # if y_field:
        #     y_field = validate_attribute_name(y_field, search_index, field_cache)
        #     if "&fields=" in url:
        #         url = url.replace("&fields=", f"&fields={y_field}")
        #     else:
        #         url += f"&fields={y_field}"
    except ValueError as ve:
        return f"""Error in attribute validation: {str(ve)}"""

    url = url.replace("query=", "x=")

    data = await make_api_request(url)
    if not data or "report" not in data:
        return f"Unable to fetch report or no report found for URL: {url}."

    if report_type == "sources":
        return format_sources_report(data, url)

    if report_type == "histogram":
        return format_histogram_report(data, url)

    return f"""{DATASTORE_NAME} Report ({report_type}):

{data['report']}

URL: {url}"""


def register_tools(mcp) -> None:
    """Register report tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(get_report)
