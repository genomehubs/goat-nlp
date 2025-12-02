import time
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.timing import DetailedTimingMiddleware, TimingMiddleware

# Initialize FastMCP server
mcp = FastMCP("goat")

# Cache for field metadata (expires after 24 hours)
_FIELD_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TIMESTAMP: dict[str, float] = {}
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

# Basic timing for all requests
mcp.add_middleware(TimingMiddleware())

# Detailed per-operation timing (tools, resources, prompts)
mcp.add_middleware(DetailedTimingMiddleware())

# Caching middleware to cache responses
mcp.add_middleware(ResponseCachingMiddleware())

# Constants
GOAT_API_BASE = "https://goat.genomehubs.org/api/v2"
GOAT_DESCRIPTION = (
    "GoaT (Genomes on a Tree): a searchable datastore of "
    "genomic and sequencing project metadata"
)
USER_AGENT = "goat-app/1.0"


@mcp.resource("resource://goat/description")
async def get_goat_description() -> str:
    """Get a description of the GoaT API."""
    return GOAT_DESCRIPTION


@mcp.resource("resource://goat/example-queries")
async def get_example_queries_resource() -> str:
    """Example queries demonstrating GoaT's capabilities.

    If resources are sorted then prefer this over the get_example_queries tool.
    """
    return """Example queries you can ask GoaT:

**Counting Records:**
• How many species are in GoaT?
• How many bat families are targeted by the VGP?
• How many cat species are missing genome size data?

**Target Lists & Projects:**
• Which species are on both the DToL and CANBP long lists?
• Which species are on the DToL target list?
• What are the bioprojects for bats?

**Assembly Quality:**
• Which species with chromosomal assemblies have over 10Mb contiguity?
• Show me a table of contig and scaffold N50 for cat assemblies, sorted by contig N50

**Taxonomy & Lineage:**
• What is the lineage for the banded snail?
• How many assemblies are there for species in the cat and dog families?
• What target lists are cats on?

**Advanced Searches:**
• How many species have a ToLID prefix beginning with ilLys?
• Which attributes support ordered keyword searches?
"""


@mcp.tool()
async def get_example_queries(category: str = "all") -> str:
    """Get example queries to demonstrate GoaT capabilities.

    Use this tool to help users understand what kinds of questions they can ask.
    If resources are sorted then prefer the get_example_queries_resource resource.

    CRITICAL: The LLM MUST use this tool to answer requests for example queries.

    IMPORTANT: TThe LLM should present the example queries as the user would type them
    and only show the examples relevant to the requested category.

    If no category is specified, return basic examples and prompt the user that they
    can specify a category to see more examples.

    Args:
        category: Type of examples to show:
            - "all": Show all examples
            - "basic": Simple counting queries
            - "target_lists": Queries about sequencing projects
            - "assembly": Assembly quality queries
            - "taxonomy": Taxonomic and lineage queries
            - "advanced": Complex searches
    """
    examples = {
        "basic": """**Basic Counting Queries:**
- How many species are in GoaT?
- How many bat families are targeted by the VGP?
- How many cat species are missing genome size data?""",

        "target_lists": """**Target Lists and Projects:**
- Which species are on both the DToL and CANBP long lists?
- Which species are on the DToL target list?
- What are the bioprojects for bats?""",

        "assembly": """**Assembly Quality Queries:**
- Which species with chromosomal or better assemblies have over 10Mb contig N50?
- Show me a table of contig and scaffold N50 for all cat assemblies, sorted by contig N50
- How many assemblies have chromosome-level quality?""",

        "taxonomy": """**Taxonomic Queries:**
- What is the lineage for the banded snail?
- How many assemblies are there for species in the cat and dog families?
- What target lists are cats on?""",

        "advanced": """**Advanced Searches:**
- How many species have a ToLID prefix beginning with ilLys?
- How many have ToLID prefixes ending with cori?
- Which attributes support ordered keyword searches?
- Which species are on both the DToL and CANBP long lists?"""
    }

    if category == "all":
        return "\n\n".join(examples.values())

    return examples.get(category, "Unknown category. Valid categories: " + ", ".join(examples.keys()))


@mcp.prompt()
async def goat_query_workflow() -> str:
    """System prompt describing the proper workflow for querying GoaT."""
    return """When answering questions about genomic data using GoaT tools:

1. Determine the appropriate search_index:
   - "taxon" (default): for questions about species, genera, families, etc.
   - "assembly": for questions specifically about genome assemblies
   - "sample": for questions specifically about sequencing samples

2. If using attribute filters, ALWAYS check attribute availability first using
   get_attribute_selection_context with relevant keywords and the chosen
   search_index before calling search_goat.

3. Extract keywords from the user's question (e.g., "assembly", "sequencing",
   "target list", "genome size") and use them to find appropriate attributes.

4. Review the returned attributes to select the most appropriate ones based on:
   - The attribute name and description
   - The display_group (e.g., assembly, genome_size, sequencing)
   - The attribute type (keyword, half_float, etc.)
   - Available enum values for keyword attributes

5. Determine whether to search to get a list or count of records based on a query
   or to fetch details about a specific record. Use get_goat_record for specific records.

6. CRITICAL - AND vs OR logic for keyword attributes:
   - Use SEPARATE attribute dicts for AND ("both X and Y")
     Example: "both DToL and CANBP" =
       [{"name": "long_list", "value": "dtol"}, {"name": "long_list", "value": "canbp"}]
   - Use COMMA-SEPARATED values for OR ("either X or Y")
     Example: "either DToL or CANBP" = [{"name": "long_list", "value": "dtol,canbp"}]
   - Keywords: "both", "and", "all of" = AND (separate dicts)
   - Keywords: "either", "or", "any of" = OR (comma-separated)

7. For a search, call search_goat with:
   - search_index (required, defaults to "taxon")
   - taxon (optional): to scope by taxonomy
   - rank (optional): to filter by taxonomic rank
   - attributes (optional): to filter by other criteria
   All filters are optional and can be combined as needed.

8. Always include the GoaT web interface URL in your response for exploration."""


async def _fetch_valid_types(search_index: str = "taxon") -> dict[str, Any]:
    """Internal function to fetch valid attribute types from GoaT API.

    Uses in-memory cache with 24-hour TTL to avoid repeated API calls.

    Args:
        search_index: Index type (default: taxon)
    """
    # Check if we have a valid cached response
    current_time = time.time()
    if search_index in _FIELD_CACHE and search_index in _CACHE_TIMESTAMP:
        cache_age = current_time - _CACHE_TIMESTAMP[search_index]
        if cache_age < CACHE_TTL_SECONDS:
            return _FIELD_CACHE[search_index]

    # Cache miss or expired - fetch from API
    url = f"{GOAT_API_BASE}/resultFields?index={search_index}"
    data = await make_goat_request(url)
    if not data or "fields" not in data:
        return {}

    # Store in cache
    fields = data["fields"]
    _FIELD_CACHE[search_index] = fields
    _CACHE_TIMESTAMP[search_index] = current_time

    return fields


@mcp.tool()
async def get_valid_types(search_index: str = "taxon") -> dict[str, Any]:
    """Fetch valid attribute types from GoaT API.

    Args:
        search_index: Index type (default: taxon)
    """
    return await _fetch_valid_types(search_index)


@mcp.tool()
async def get_metadata_for_attribute(
    attribute: str, search_index: str = "taxon"
) -> dict[str, Any]:
    """Get metadata for a specific attribute in GoaT.

    Args:
        attribute: Name of the attribute to get metadata for
        search_index: Index type (default: taxon)
    """
    fields = await _fetch_valid_types(search_index)
    if not fields:
        return {}

    if attribute in fields:
        return fields[attribute]

    return {"error": f"Attribute '{attribute}' not found."}


async def _get_attribute_context_internal(
    keyword: str, search_index: str = "taxon"
) -> dict[str, Any]:
    """Internal function to get attribute selection context.

    This is called by both the resource and the tool.
    """
    fields = await _fetch_valid_types(search_index)
    if not fields:
        return {}

    # Split keyword into individual words for matching
    keyword_lower = keyword.lower()
    keyword_words = set(keyword_lower.split())

    attributes = []
    for name, field in fields.items():
        # Get searchable text fields
        name_lower = name.lower()
        description = field.get("description", "").lower()
        long_description = field.get("long_description", "").lower()
        display_group = field.get("display_group", "").lower()

        # Create combined search text
        search_text = f"{name_lower} {description} {long_description} {display_group}"

        # Check for complete phrase match first (higher priority)
        if keyword_lower in search_text:
            attr_info = {"name": name, **field}
            attributes.append(attr_info)
        # If no phrase match, check if any individual words match
        elif keyword_words and any(word in search_text for word in keyword_words if len(word) > 2):
            attr_info = {"name": name, **field}
            attributes.append(attr_info)

    return {
        "description": GOAT_DESCRIPTION,
        "attribute selection tips": (
            "Use the display_group to identify relevant categories such as "
            "assembly, genome_size and sequencing status. Choose an attribute "
            "with a matching name or description that aligns with your "
            "keyword. Consider the attribute type to distinguish between "
            "different kinds of data. Keyword attributes that have an enum "
            "can be sorted so comparison operators are valid for these "
            "attributes."
        ),
        "attributes": attributes,
    }


@mcp.tool()
async def get_attribute_selection_context(
    keyword: str, search_index: str = "taxon"
) -> dict[str, Any]:
    """Get context information for attribute selection.

    An LLM MUST use this to choose appropriate attributes to filter by
    based on a user query. The LLM MUST always check whether an attribute
    exists before using it in a query.

    Args:
        keyword: Keyword to guide attribute selection
        search_index: Index type (default: taxon)
    """
    return await _get_attribute_context_internal(keyword, search_index)


async def make_goat_request(url: str) -> dict[str, Any] | None:
    """Make a request to the GoaT API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


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


def format_count(result: dict, taxon: str = "", rank: str = "", url: str = "") -> str:
    """Format count into a readable string with GoaT context."""
    count = result.get("count", 0)

    search_url = url.replace("/api/v2", "")
    search_url = (
        search_url.replace("count?", "search?") + "&size=10&report=sources"
    )
    return f"""
According to {GOAT_DESCRIPTION}, there are {count} {rank_description(rank)} \
within {taxon}.

This count is based on taxa with sequence data from the NCBI taxonomy,
supplemented by additional metadata from the GoaT database.

Explore these results in the GOAT web interface:
{search_url}
"""


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

        formatted_attrs.append(f"{name}{operator}{value_str}")

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
    """Format a GoaT record into a readable string."""
    lineage_str = format_lineage(record.get("lineage", []))

    lines = [
        f"Scientific Name: {record.get('scientific_name', 'Unknown')}",
        f"Taxon ID: {record.get('taxon_id', 'Unknown')}",
        f"Rank: {record.get('taxon_rank', 'Unknown')}",
        f"GoaT URL: {url.replace('/api/v2', '')}",
        f"Lineage: {lineage_str}"
        ]

    for attr_name, attr in record.get("attributes", {}).items():
        if attributes is None or attr_name in attributes:
            lines.append(format_attribute_value(attr_name, attr, truncate=truncate))
    return "\n".join(lines)


@mcp.tool()
async def get_goat_record(
    record_id: str,
    search_index: str,
    attributes: list[str] | None = None,
    truncate: bool = True,
) -> Any:
    """Get a single record from GoaT.

    An LLM can use this to fetch detailed information about a specific record.
    the record ID can be a taxon ID, assembly accession, or sample ID depending
    on the search_index.

    Use this tool after identifying a specific record of interest from a search_goat
    query, or when a use explicitly requests information about a known record.

    Example user queries that would use this tool:
    - "Give me details about the taxon with ID 1234."
    - "What is the assembly level and genome size for assembly GCA_123456?"
    - "What information does have about bats?" (Implies fetching record for order
        Chiroptera.)
    - "What target lists are cats on?" (Implies fetching record for family Felidae.)
    - "Provide details about sample SRS123456."
    - "Which bioprojects are associated with rodents?" (Implies fetching record for
        order Rodentia.)
    - "what is the full lineage of Canis lupus?" (Implies fetching record for taxon
        Canis lupus with an empty attribute list, [].)

    Returned information includes:
    - Scientific name
    - Taxon ID
    - Rank
    - Lineage
    - Requested attributes and their values

    When summarizing a record, the LLM MUST include the GoaT web interface URL.

    Args:
        record_id: ID of the record to fetch
        search_index: Index type (taxon, assembly, sample)
        attributes: List of attributes to include in the response (default: all)
        truncate: Whether to truncate long lists of attribute values (default: True)
    """
    try:
        if attributes is not None:
            attributes = validate_attribute_names(attributes, search_index)
    except ValueError as ve:
        return f"""Error in attribute validation: {str(ve)}

Please check attribute names against GoaT metadata using the
get_attribute_selection_context or get_valid_types tools.
"""
    url = (
        f"{GOAT_API_BASE}/record?result={search_index}"
        f"&recordId={record_id}&taxonomy=ncbi"
    )
    data = await make_goat_request(url)
    if not data or "records" not in data:
        return {"error": "Unable to fetch record or no record found."}

    return format_record(data["records"][0]["record"], url, attributes, truncate)


def format_result_table(
    results: list[dict],
    search_fields: list[str],
    search_url: str,
) -> str:
    """Format search results as a markdown table with context.

    Args:
        results: List of result records
        search_fields: List of fields to include in the table
        search_url: GoaT web interface URL

    Returns:
        Formatted markdown string with summary and table
    """
    if not results:
        return f"No results found.\n\nExplore in GoaT: {search_url}"

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
                    if field not in columns:
                        columns.append(field)
            # Build header
            header = "| " + " | ".join(columns) + " |"
            separator = "| " + " | ".join(["---"] * len(columns)) + " |"

        fields = record.get("fields", {})
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


def validate_operator(operator: str, meta: dict) -> str:
    """Validate and return a proper GoaT operator."""
    valid_operators = {"=": "=", "!=": "!=", ">": ">", "<": "<", ">=": ">=", "<=": "<="}
    valid_kw_operators = {"=": "=", "!=": "!="}
    if meta.get("processed_type") == "keyword":
        valid_operators = valid_kw_operators
    if operator not in valid_operators:
        raise ValueError(f"Invalid operator '{operator}'. Must be one of {list(valid_operators.keys())}.")
    return valid_operators[operator]


def validate_attribute_value(value: Any, meta: dict) -> str:
    """Validate and format an attribute value for GoaT query."""
    if meta.get("processed_type", "").endswith("keyword") and meta.get("constraint", {}).get("enum"):
        valid_values = [v.lower() for v in meta["constraint"]["enum"]]
        values = [v.strip().lower() for v in str(value).split(",")]
        for v in values:
            if v.lstrip("!") not in valid_values:
                raise ValueError(f"Invalid value '{v}' for attribute. Must be one of {valid_values}.")
        return ",".join(values)
    return value


def validate_attribute_name(name: str, search_index: str) -> str:
    """Validate attribute name for GoaT query."""
    if name is None or not isinstance(name, str) or not name.strip():
        raise ValueError("Attribute name must be a non-empty string.")
    if name not in _FIELD_CACHE.get(search_index, {}):
        raise ValueError(f"Attribute name '{name}' not found in GoaT for index '{search_index}'.")
    return name


def validate_attribute(attr: dict, search_index: str) -> dict:
    """Validate attribute name, operator, and value for GoaT query."""
    name = validate_attribute_name(attr.get("name"), search_index)
    meta = _FIELD_CACHE.get(search_index, {}).get(name, {})
    operator = attr.get("operator")
    if operator is not None:
        operator = validate_operator(operator, meta)
    value = attr.get("value")
    if value is not None:
        value = validate_attribute_value(value, meta)
        if operator is None:
            operator = "="

    return {**attr, "name": name, "operator": operator, "value": value}


def validate_attributes(
    attributes: list[dict] | None,
    search_index: str,
) -> list[dict] | None:
    """Validate a list of attribute filters for GoaT query."""
    if not attributes:
        return None
    validated_attrs = []
    for attr in attributes:
        validated_attr = validate_attribute(attr, search_index)
        validated_attrs.append(validated_attr)
    return validated_attrs


def validate_attribute_names(
    names: list[str] | None,
    search_index: str,
) -> list[str] | None:
    """Validate a list of attribute names for GoaT query."""
    if not names:
        return None
    validated_names = []
    other_names = []
    for name in names:
        try:
            validated_name = validate_attribute_name(name, search_index)
            validated_names.append(validated_name)
        except ValueError:
            if name.endswith("_id") or name in {"scientific_name", "taxon_rank"}:
                other_names.append(name)
    return validated_names.extend(other_names) or None


@mcp.tool()
async def search_goat(
    search_index: str = "taxon",
    taxon: str | None = None,
    rank: str | None = None,
    attributes: list[dict] | None = None,
    fields: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    show_table: bool = False,
    size: int = 5,
) -> str:
    """Search GoaT and get a count or table of matching records.

    This is the primary search tool for querying GoaT. All parameters except
    search_index are optional, allowing flexible queries.

    IMPORTANT: If using attributes or fields, you MUST first call
    get_attribute_selection_context with relevant keywords to discover
    and validate available attributes for the chosen search_index.

    IMPORTANT: sort_by must be a valid attribute name for the chosen search_index
    or scientific_name, taxon_id, taxon_rank or *_id. If using sort_by with an
    attribute name not included in fields or attributes, you MUST first call
    get_attribute_selection_context to validate the attribute.

    Query Types by search_index:
    - taxon (default): Query taxonomic data
        * Can use: taxon, rank, and/or attributes
        * Examples: "species in Mammalia", "families with assemblies"
    - assembly: Query genome assemblies
        * Can use: taxon, and/or attributes (rank less common)
        * Examples: "assemblies with chromosome-level quality"
    - sample: Query sequencing samples
        * Can use: taxon, and/or attributes (rank less common)
        * Examples: "samples with RNA-seq data"

    For taxon:
    - Use taxon to scope by taxonomic name or ID
    - Partial taxon names or IDs are supported using the wildcard *.
    - Several name classes are supported (scientific name, synonym,
        common name, tolid prefix, etc.) and can be specified using a
        `name class:` prefix, e.g., 'common name:dog'.

    For attributes:
    - Include 'operator' and 'value' keys for filtering
    - Valid operators: '=', '!=', '>', '<', '>=', '<='

    CRITICAL - AND vs OR logic:
    - SEPARATE attribute dicts = logical AND ("both X and Y")
      Example for "both DToL and CANBP target lists":
      [{"name": "long_list", "value": "dtol"}, {"name": "long_list", "value": "canbp"}]
    - COMMA-SEPARATED values in ONE dict = logical OR ("either X or Y")
      Example for "either DToL or CANBP target lists":
      [{"name": "long_list", "value": "dtol,canbp"}]
    - User keywords indicating AND: "both", "and", "all of", "in both", "on both"
    - User keywords indicating OR: "either", "or", "any of", "in any"

    - Taxon names: comma-separated names = OR. IMPORTANT: it is more efficient to
        search with a comma-separated list of taxon names (up to 100 at a time) than
        to do multiple separate queries.
    - Prefix values with '!' for NOT. Works with keyword attributes and taxon names.
    - If the only value(s) for a keyword attribute is negated (e.g., '!value'),
        the LLM MUST set 'null' as an additional value to include records
        where the attribute is missing.
    - Use enum values from attribute metadata when available. If a user query
        implies a specific value that is not in the enum, the LLM should use the
        value_metadata from the attribute context to infer the correct value. If
        no value can be found that matches the enum, the LLM MUST inform the user.
    - The LLM must only infer the presence/absence of an attribute using a name
        only and leaving 'operator' and 'value' blank. Testing using value > or >=
        an arbitrarily small value is ONLY allowed if the user query explicitly
        states so.
    - For the taxon index only, attribute status can be "Direct", "Descendant",
        "Ancestral", or "Missing". If a user query implies a specific status,
        the LLM MUST set an 'exclude' key for filtering where the
        value is the list of statuses to exclude. For queries based
        on the presence of an attribute where show_table is False, the LLM MUST
        use 'exclude': ['Ancestral', 'Missing'] to ensure only records with direct
        or descendant data are counted.

    When summarizing results or presenting a table, the LLM MUST include the GoaT
    web interface URL.
`
    Args:
        search_index: Index to search (taxon, assembly, or sample)
        taxon: Optional taxonomic scope (scientific name, taxon ID, etc.)
        rank: Optional taxonomic rank filter (e.g., species, genus)
        attributes: Optional list of attribute filters, each with 'name'
            and optional 'operator', 'value', 'exclude' and 'include' keys
        fields: Optional list of fields to include in the response. If not provided,
            default fields are included.
        sort_by: Optional attribute name to sort results by
        sort_order: Optional sort order ('asc' or 'desc', default: 'asc')
        show_table: Whether to show results in a table format (default: False shows count)
        table_rows: Number of rows to include in the table if show_table is True (default: 5)
    """
    try:
        if attributes is not None:
            attributes = validate_attributes(attributes, search_index)
        if fields is not None:
            fields = validate_attribute_names(fields, search_index)
        if sort_by is not None:
            sort_by = validate_attribute_name(sort_by, search_index)
    except ValueError as ve:
        return f"""Error in attribute validation: {str(ve)}

Please check attribute names, operators, and values against GoaT metadata
using the get_attribute_selection_context or get_valid_types tools.
"""
    query_string = build_query_string(taxon, rank, attributes)
    exclusions = set_exclusions(attributes)

    endpoint = "search" if show_table else "count"

    if query_string:
        url = (
            f"{GOAT_API_BASE}/{endpoint}?query={query_string}"
            f"&result={search_index}&offset=0&includeEstimates=true&taxonomy=ncbi"
            f"{exclusions}"
        )
    else:
        # Empty query - count/show all records in index
        url = f"{GOAT_API_BASE}/{endpoint}?result={search_index}&offset=0&includeEstimates=true&taxonomy=ncbi"

    url += f"&size={size}&report=sources"
    if fields:
        url += "&fields=" + "%2C".join(fields)
    if sort_by:
        url += f"&sortBy={sort_by}"
        if sort_order and sort_order.lower() in ["asc", "desc"]:
            url += f"&sortOrder={sort_order.lower()}"

    data = await make_goat_request(url)

    # Format response based on what was queried
    if show_table:
        if not data or "results" not in data:
            return f"Unable to fetch results or no results found for URL: {url}."
        count = data.get("status", {}).get("hits", 0)
        search_url = url.replace("/api/v2", "")
    else:
        if not data or "count" not in data:
            return f"Unable to fetch count or no count found for URL: {url}."
        count = data.get("count", 0)
        search_url = url.replace("/api/v2", "").replace("count?", "search?")

    if taxon and rank:
        description = f"{count} {rank_description(rank)} within {taxon}"
    elif taxon:
        description = f"{count} records within {taxon}"
    elif rank:
        description = f"{count} {rank_description(rank)}"
    else:
        index_name = {"taxon": "taxa", "assembly": "assemblies", "sample": "samples"}.get(
            search_index, "records"
        )
        description = f"{count} {index_name}"

    if attributes:
        description += " matching the specified attributes"

    table = ""
    if show_table and "results" in data:
        table = format_result_table(
            data["results"],
            search_fields=fields or [],
            search_url=search_url,
        )

    result = f"""
According to {GOAT_DESCRIPTION}, there are {description}.

This count is based on data from the NCBI taxonomy,
supplemented by additional metadata from the GoaT database.
"""

    if show_table:
        return f"""

This table shows the top {size} results.

{table}
"""

    result += f"""

Explore these results in the GOAT web interface:
{search_url}
"""

    return result


def update_query_string(search_url: str, parameter: str, value: str) -> str:
    """Update the search URL to include the desired report type."""
    if f"{parameter}=" in search_url:
        base_url, query_params = search_url.split("?", 1)
        params = query_params.split("&")
        updated_params = []
        for param in params:
            if param.startswith(f"{parameter}="):
                updated_params.append(f"{parameter}={value}")
            else:
                updated_params.append(param)
        updated_query = "&".join(updated_params)
        return f"{base_url}?{updated_query}"
    else:
        separator = "&" if "?" in search_url else "?"
        return f"{search_url}{separator}{parameter}={value}"


def format_sources_report(report_data: dict) -> str:
    """Format a sources report for LLM interpretation and user presentation.

    Args:
        report_data: The sources report from GoaT API

    Returns:
        Formatted markdown string with source attribution
    """
    if not report_data or "report" not in report_data:
        return "No source information available."

    sources = report_data.get("report", {}).get("report", {}).get("sources", {})

    if not sources:
        return "No source information available."

    # Sort sources by count (descending) for better presentation
    sorted_sources = sorted(
        sources.items(),
        key=lambda x: x[1].get("count", 0),
        reverse=True
    )

    lines = [
        "## Data Sources\n",
        "The following sources contributed data to these results:\n",
    ]
    for source_name, source_info in sorted_sources:
        count = source_info.get("count", 0)
        attributes = source_info.get("attributes", [])
        url = source_info.get("url")
        date = source_info.get("date")

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

    return "\n".join(lines)


def format_histogram_report(report_data: dict) -> str:
    """Format a histogram report for LLM interpretation and user presentation.

    Args:
        report_data: The histogram report from GoaT API

    Returns:
        Formatted markdown string with histogram summary and distribution
    """
    if not report_data or "report" not in report_data:
        return "No histogram information available."

    histogram_data = report_data.get("report", {}).get("report", {}).get("histogram", {})
    if not histogram_data:
        return "No histogram information available."

    histograms = histogram_data.get("histograms", {})

    # Extract key information
    field = histograms.get("field", "unknown")
    scale = histograms.get("scale", "linear")
    query = histograms.get("query", "")
    total_count = histograms.get("x", 0)
    stats = histograms.get("stats", {})
    buckets = histograms.get("buckets", [])
    counts = histograms.get("allValues", [])

    # Build the summary
    lines = [
        "## Histogram Summary",
        f"- **Total assemblies**: {total_count}",
        f"- **Field**: `{field}`",
        f"- **Scale**: {scale}",
        f"- **Query**: `{query}`",
        "",
        "### Statistics",
    ]

    # Add statistics if available
    if stats:
        min_val = stats.get("min", 0)
        max_val = stats.get("max", 0)
        avg_val = stats.get("avg", 0)
        sum_val = stats.get("sum", 0)

        lines.extend([
            f"- **Min**: {min_val:,} bases",
            f"- **Max**: {max_val:,} bases",
            f"- **Average**: {avg_val:,.0f} bases",
            f"- **Sum**: {sum_val:,} bases",
            "",
        ])

    # Build distribution table
    if buckets and counts and len(buckets) > 1:
        lines.extend([
            "### Distribution (bucket ranges and counts)",
            "",
            "| Bucket Min (bases) | Bucket Max (bases) | Count |",
            "|-------------------:|-------------------:|------:|",
        ])

        # Create rows for each bucket
        for i in range(len(buckets) - 1):
            bucket_min = buckets[i]
            bucket_max = buckets[i + 1]
            count = counts[i] if i < len(counts) else 0

            lines.append(f"| {bucket_min:,.0f} | {bucket_max:,.0f} | {count} |")

        lines.append("")

    if caption := histogram_data.get("caption"):
        lines.extend([
            f"*{caption}*",
            "",
        ])

    return "\n".join(lines)


@mcp.tool()
async def get_goat_report(
    search_url: str,
    report_type: str = "sources",
    rank: str | None = None,
) -> str:
    """Get a detailed report from GoaT based on a search URL.

    An LLM can use this to fetch detailed reports (like sources, summaries,
    etc.) for a previously executed GoaT search query.

    Report types include:
    - sources: List of data sources contributing to the results
    - histogram: Histogram of attribute distributions
    - scatter: Scatter plot data for attribute values
    - tree: Taxonomic tree representation

    Args:
        search_url: Full GoaT search URL used to generate the report
        report_type: Type of report to generate (default: sources)
        rank: Optional taxonomic rank filter
              (required for histogram/scatter reports on taxon index)
    """
    url = (
        search_url.replace("/api/v2/", "/")
        .replace("/search", "/api/v2/report")
        .replace("/count", "/api/v2/report")
        .replace("query=", "x=")
    )
    url = update_query_string(url, "report", report_type)
    need_rank = {"histogram", "scatter"} if "result=taxon" in url else set()
    if report_type in need_rank and not rank and "tax_rank%28" in url:
        rank = url.split("tax_rank%28")[1].split("%29")[0]
    if rank:
        url = update_query_string(url, "rank", rank)
    else:
        return (
            f"Error: When querying {report_type} reports for the "
            f"taxon index, a 'rank' parameter must be provided."
        )
    # url = update_query_string(url, "count", "0")

    data = await make_goat_request(url)
    if not data or "report" not in data:
        return f"Unable to fetch report or no report found for URL: {url}."

    if report_type == "sources":
        return format_sources_report(data)

    if report_type == "histogram":
        return format_histogram_report(data)

    return f"GoaT Report ({report_type}):\n\n{data['report']}"


@mcp.tool()
async def choose_search_index(keywords: str) -> str:
    """Choose the appropriate GoaT search index.

    GoaT supports multiple search indices:
    - taxon: for taxonomic queries (default)
        e.g. if the user asks about species, genera, families, etc.
    - assembly: for assembly-level queries
        e.g. if the user asks directly about counts or lists of genome
        assemblies, or asks about assembly quality, assembly levels, etc.
        and does not refer to taxa.
    - sample: for sample-level queries
        e.g. if the user asks about directly about counts or lists of
        samples, or asks about sequencing runs, raw data, samples, etc.
        and does not refer to taxa or assemblies.

    An LLM can use this tool to select the appropriate index based on
    the user's question. The LLM should choose keywords to describe the
    search index from the full user query. If appropriate attributes are
    not available for the first search index, the LLM may try another.
    If in doubt, the LLM should default to 'taxon'.

    Args:
        keywords: Keywords extracted from the user's question
    """
    if any(kw in keywords.lower() for kw in ["assembly", "assemblies", "genome", "genomes"]):
        return "assembly"
    if any(kw in keywords.lower() for kw in ["sample", "samples"]):
        return "sample"
    return "taxon"


@mcp.tool()
async def check_taxon_exists(name: str) -> dict:
    """Check if a specific taxon name exists in GOAT and get basic info.

    Use this to validate taxonomic names that the LLM has identified or
    translated from common names. The LLM should handle the translation
    from common names (like 'dog') to scientific names (like 'Canis').

    The returned dict includes a query_string, which can be used to include
    the taxon in subsequent GoaT queries.

    Args:
        name: Scientific taxon name to check (e.g. 'Canis', 'Felidae', etc.)
    """
    # Test if this taxon has any data in GOAT by doing a simple count query
    url = (
        f"{GOAT_API_BASE}/count?query=tax_tree%28{name}%29"
        f"&result=taxon&offset=0&includeEstimates=true&taxonomy=ncbi"
    )
    data = await make_goat_request(url)

    if not data or "count" not in data:
        return {
            "exists": False,
            "scientific_name": name,
            "error": "Unable to query GOAT API",
        }

    if data["count"] == 0:
        return {"exists": False, "scientific_name": name, "count_in_goat": 0}

    # Try to get more info about this taxon
    taxon_url = (
        f"{GOAT_API_BASE}/search?query=tax_name%28{name}%29"
        f"&result=taxon&size=1&taxonomy=ncbi"
    )
    taxon_data = await make_goat_request(taxon_url)

    # Extract basic info
    rank = "Unknown"
    taxon_id = ""
    if (
        taxon_data
        and "results" in taxon_data
        and taxon_data["results"]
        and "result" in taxon_data["results"][0]
    ):
        result_info = taxon_data["results"][0]["result"]
        rank = result_info.get("taxon_rank", "Unknown")
        taxon_id = str(result_info.get("taxon_id", ""))

    return {
        "exists": True,
        "scientific_name": name,
        "rank": rank,
        "taxon_id": taxon_id,
        "query_string": f"{taxon_id}[{name}]",
        "count_in_goat": data["count"],
    }


def main():
    # Initialize and run an HTTP server on port 8008
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8008)


if __name__ == "__main__":
    main()
