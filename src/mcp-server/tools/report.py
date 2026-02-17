from ..config import API_BASE, DATASTORE_NAME
from ..logging_config import get_logger
from .artifact_store import retrieve
from .helpers.api import make_api_request
from .helpers.axis import axis_opts_to_string
from .helpers.errors import artifact_retrieval_error, invalid_intent_error
from .helpers.query import (
    build_search_params,
    build_user_facing_url,
    params_dict_to_url,
)

logger = get_logger(__name__)


GET_REPORT_PROMPT = f"""Generate {DATASTORE_NAME} reports with different visualisation types.

CHOOSE YOUR REPORT TYPE AND PROVIDE THE REQUIRED PARAMETERS:

**DISTRIBUTION REPORTS** (show data across axes):

1. **histogram**: Distribution of values for one attribute
   Required: x_axis (field/rank/attribute distribution)
   Optional: category (group by field/rank), bin_count, scale
   Example: "What is the distribution of genome sizes?"
            → process_axis(axis_definition="genome_size") → get_report(intent="histogram", x_axis_artifact_id=...)

2. **scatter**: Relationship between two attributes
   Required: x_axis, y_axis (both field/rank/attribute distributions)
   Optional: category, scale
   Example: "How do genome size and chromosome count compare?"
            → process_axis(x...) + process_axis(y...) → get_report(intent="scatter", x_axis=..., y_axis=...)

3. **tree**: Taxonomic tree with optional data bars on leaves
   Required: none
   Optional: y_axis (data to show at leaves), category
   Example: "Show the taxonomy tree for mammals with genome size data at leaves"
            → process_axis(y...) → get_report(intent="tree", y_axis_artifact_id=...)

4. **map**: Geographic distribution
   Required: none
   Optional: category (group by attribute/rank)
   Example: "Where are these species found?"
            → process_axis(category...) → get_report(intent="map", category_artifact_id=...)

**COMPOSITION REPORTS** (show proportions within hierarchies):

5. **donut**: What proportion of results match an additional filter?
   Required: Required: parent_filter (the broader context to show proportions within)
   Example: "Of the mammal species, what proportion have genome_size > 3G?"
            → process_attributes(filter for genome_size > 3G)
            → get_report(intent="donut", parent_filter_artifact_id=...)

6. **rainbow**: What proportion at each rank match filter_y, and optionally filter_z?
   Required: parent_filter (first level filter)
   Example: "Of mammals with genome_size > 3G, how many per phylum and order?"
            → process_attributes(genome_size > 3G) → process_attributes(additional...)
            → get_report(intent="rainbow", parent_filter_artifact_id=...)

7. **sources**: Data sources for this query
   Required: none
   Example: "Which databases contributed to these results?"
            → get_report(intent="sources")
"""


async def get_report(
    user_query: str,
    intent: str,  # This tells us what the other params mean
    identifiers_artifact_id: str,
    attributes_artifact_id: str,
    # Visualisation axes (for histogram, scatter, tree, map)
    x_axis_artifact_id: str | None = None,  # Required: histogram, scatter
    y_axis_artifact_id: str | None = None,  # Required: scatter; Optional: tree
    category_artifact_id: str | None = None,  # Optional: histogram, scatter, tree, map
    # Hierarchical filters (for donut, rainbow)
    parent_filter_artifact_id: str | None = None,  # "broader scope for main query"
    search_index: str = "taxon",
) -> dict[str, str]:
    """Generate a report with visualisation.

    Retrieves axis and filter artifacts, composes query, calls API, formats output.
    """

    # If artifact tokens were provided (string), attempt to retrieve stored objects
    if isinstance(identifiers_artifact_id, str):
        identifiers_output = retrieve(identifiers_artifact_id)
    if isinstance(attributes_artifact_id, str):
        attributes_output = retrieve(attributes_artifact_id)

    if not isinstance(identifiers_output, dict):
        raise ValueError(artifact_retrieval_error("identifiers", "get_report"))
    if not isinstance(attributes_output, dict):
        raise ValueError(artifact_retrieval_error("attributes", "get_report"))

    valid_intents = {"histogram", "scatter", "tree", "donut", "rainbow", "map"}
    if intent not in valid_intents:
        raise ValueError(
            invalid_intent_error(intent, valid_intents, "get_report")
        )

    # Extract identifiers
    taxa = identifiers_output.get("taxa", [])
    assemblies = identifiers_output.get("assemblies", [])
    samples = identifiers_output.get("samples", [])
    taxon_filter_type = identifiers_output.get("taxon_filter_type", "children")
    rank = identifiers_output.get("rank")

    # Extract attributes
    attributes = attributes_output.get("attributes", [])
    fields = attributes_output.get("fields", [])
    names = attributes_output.get("names", [])
    ranks = attributes_output.get("ranks", [])

    # Retrieve axis and filter artifacts if provided
    x_axis = None
    if x_axis_artifact_id and isinstance(x_axis_artifact_id, str):
        x_axis = retrieve(x_axis_artifact_id)
        print(f"Retrieved x_axis artifact: {x_axis}")

    y_axis = None
    if y_axis_artifact_id and isinstance(y_axis_artifact_id, str):
        y_axis = retrieve(y_axis_artifact_id)

    category = None
    if category_artifact_id and isinstance(category_artifact_id, str):
        category = retrieve(category_artifact_id)

    parent_filter = None
    if parent_filter_artifact_id and isinstance(parent_filter_artifact_id, str):
        parent_filter = retrieve(parent_filter_artifact_id)

    # Build base search params as dict
    params = await build_search_params(
        search_index=search_index,
        taxa=taxa,
        taxon_filter_type=taxon_filter_type,
        assemblies=assemblies,
        samples=samples,
        rank=rank,
        attributes=attributes,
        fields=fields,
        names=names,
        ranks=ranks,
    )

    logger.info(f"Built base search params for {intent} report: {params}")

    # Add report-specific parameters to params dict
    params["report"] = intent

    x_field = None

    # Add axis parameters for distribution reports
    if intent in {"histogram", "scatter", "tree"}:
        if x_axis:
            # x_axis should be from process_axis() output
            if isinstance(x_axis, dict) and "field_or_rank" in x_axis:
                params["x"] = x_axis["field_or_rank"]
                if not x_axis.get("is_rank"):
                    x_field = x_axis["field_or_rank"]
                    # Extract just the field names from the fields dicts
                    field_names = [f.get("name") for f in fields if isinstance(f, dict)]
                    if x_field not in field_names:
                        # If the x_axis field is not already in the fields list, add it as a name string
                        params["fields"] = field_names + [x_field]
                # if x_axis.get("modifiers"):
                #     params["xMod"] = ",".join(x_axis["modifiers"])
                params["xOpts"] = axis_opts_to_string(x_axis, is_cat=x_axis.get("is_rank", False))

        if intent == "scatter" and y_axis:
            # y_axis required for scatter
            if isinstance(y_axis, dict) and "field_or_rank" in y_axis:
                params["y"] = y_axis["field_or_rank"]
                if y_axis.get("modifiers"):
                    params["yMod"] = ",".join(y_axis["modifiers"])
                params["yOpts"] = axis_opts_to_string(y_axis, is_cat=y_axis.get("is_rank", False))

        if intent == "tree" and y_axis:
            # y_axis optional for tree (data at leaves)
            if isinstance(y_axis, dict) and "field_or_rank" in y_axis:
                params["y"] = y_axis["field_or_rank"]
                if y_axis.get("modifiers"):
                    params["yMod"] = ",".join(y_axis["modifiers"])
                params["yOpts"] = axis_opts_to_string(y_axis, is_cat=y_axis.get("is_rank", False))

    # Add category parameter (grouping axis)
    if category and isinstance(category, dict) and "field_or_rank" in category:
        cat = category["field_or_rank"]
        catOpts = axis_opts_to_string(category, is_cat=True)
        params["cat"] = f"{cat}{catOpts}" if catOpts else cat

    # Add filter for composition reports (donut, rainbow)
    if intent in {"donut", "rainbow"} and parent_filter:
        if isinstance(parent_filter, dict) and "attributes" in parent_filter:
            # parent_filter contains base attributes for the composition
            # This would be handled by merging into attributes instead
            logger.info(f"Using parent_filter for {intent}: {parent_filter}")

    if x_field is not None:
        x_query = params.get("query", "").split(" AND ")
        if x_query[0] != x_field:
            x_query.insert(0, x_field)
            params["x"] = " AND ".join(x_query).strip()
            params.pop("query", None)

    params["rank"] = rank  # Ensure rank is included in params for API

    # Convert params dict to URL
    api_url = params_dict_to_url(f"{API_BASE}/report", params)

    logger.info(f"Report API URL: {api_url}")

    # Make API request
    data = await make_api_request(api_url)

    # Build user-facing URL
    report_url = build_user_facing_url(api_url)

    # Format response
    result = f"""
Report generated for {intent} visualisation.

Query: {user_query}

Report URL:
{report_url}

Raw API response: {data}
"""

    return {
        "user_query": user_query,
        "report": result,
    }


get_report.__doc__ = GET_REPORT_PROMPT


def register_tools(mcp) -> None:
    """Register report tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(get_report)
