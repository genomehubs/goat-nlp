"""Query parser tool for extracting structured query components from user questions."""

import time
from typing import Any

from ..config import DATASTORE_NAME
from ..logging_config import get_logger, log_tool_usage
from .artifact_store import retrieve
from .helpers.constants import FIELD_CACHE
from .helpers.errors import (
    ToolExecutionError,
    artifact_retrieval_error,
    format_unhandled_error_for_issue,
    invalid_intent_error,
    unsupported_intent_error,
)
from .helpers.fetch import fetch_valid_types
from .helpers.formatting import format_result_table, process_result_table
from .helpers.query import set_search_tips
from .helpers.search_index import resolve_index
from .helpers.validation import validate_attribute_name

logger = get_logger(__name__)


SUBMIT_QUERY_PROMPT = f"""Execute a {DATASTORE_NAME} query by parsing artifact IDs into
structured parameters and returning results.

⚠️  CRITICAL: Pass the EXACT artifact keys from process_identifiers() and process_attributes()
   WITHOUT any modification. Do not reconstruct these objects yourself.

PARAMETERS:

1. **identifiers_artifact_id**: Output artifact ID from process_identifiers()
   - Contains: taxa, filter type, rank (if detected), and the original user query

2. **attributes_artifact_id**: Output artifact ID from process_attributes()
   - Contains: attribute filters, fields to display, and field metadata

3. **intent**: Result type (choose one)
   - "count": Return count of matching records only
   - "table": Return count + paginated results as raw data (single query - do NOT call again!)
   - "sources": Return count + data sources information
   - Note: If there is ambiguity between wanting a full list/table or some
       representative examples, use intent table with a small page_size.

4. **sort_by**: (for intent="table") Field name to sort results by (e.g., "genome_size")

5. **sort_order**: (for intent="table") Sort direction - "asc" or "desc"

6. **size**: (for intent="table") Number of results per page (default: 10)

   **Strategy:** Choose size based on query intent, not just result count.
   - **Small (10-50)**: For exploratory/discovery queries where user wants a summary first
   - **Large (100-1000)**: When user explicitly asks for a list, table, or file (use pagination if count > 1000)
   - Maximum page size is 1000; recommended max for regular queries is 100

7. **page**: (for intent="table") Page number for pagination (default: 1)

8. **response_format**: Format for optional pre-formatted output (determines response envelope content)
   - "data" (default): Structured data with raw results
   - "markdown": Adds `markdown` field with formatted table
   - "csv": Adds `csv` field with CSV-formatted table
   - "full": Includes all optional fields (markdown, csv, sources)

RESPONSE ENVELOPE:

All responses include (when applicable):
- `user_query`: Original query for context
- `search_tips`: Suggestions for refining or extending the query
- `count`: Total number of matching records
- `url`: Interactive search URL in {DATASTORE_NAME} web interface
- `search_index`: Index used ("taxon", "assembly", or "sample")

For intent="table" responses, also includes:
- `results`: Raw result records (list of record dicts)

For response_format="markdown" or "full":
- `markdown`: Pre-formatted markdown table of results

For response_format="csv" or "full":
- `csv`: Pre-formatted CSV output of results

For response_format="full" (future):
- `sources`: Data provenance and source information

EXAMPLES:

Count query:
```
submit_query(
    identifiers_artifact_id="aebc12345...",
    attributes_artifact_id="fghd67890...",
    intent="count"
)
```
Returns: user_query, search_tips, count, url, search_index

Table query with markdown formatting:
```
submit_query(
    identifiers_artifact_id="aebc12345...",
    attributes_artifact_id="fghd67890...",
    intent="table",
    size=10,
    page=1,
    response_format="markdown"
)
```
Returns: All table fields + pre-formatted markdown table

"""


async def submit_query(
    identifiers_artifact_id: str,
    attributes_artifact_id: str,
    intent: str,
    search_index: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    size: int | None = None,
    page: int = 1, response_format: str = "data",
) -> dict[str, Any]:
    """Execute a query with parsed identifiers and attributes, returning results based on intent.

    This function orchestrates the full query pipeline: validates inputs, delegates to
    advanced_search for core execution, and formats results for the response format.
    See SUBMIT_QUERY_PROMPT for detailed LLM instructions.
    """

    start = time.time()

    user_query = "unknown"

    result = "not reached"

    try:

        # If artifact tokens were provided (string), attempt to retrieve stored objects
        if isinstance(identifiers_artifact_id, str):
            identifiers_output = retrieve(identifiers_artifact_id)
        if isinstance(attributes_artifact_id, str):
            attributes_output = retrieve(attributes_artifact_id)

        if not isinstance(identifiers_output, dict):
            raise ValueError(artifact_retrieval_error("identifiers", "submit_query"))
        if not isinstance(attributes_output, dict):
            raise ValueError(artifact_retrieval_error("attributes", "submit_query"))

        search_index = resolve_index(search_index, identifiers_output, attributes_output)

        if intent not in {"count", "sources", "table"}:
            if intent in {"histogram", "scatter", "tree", "donut", "rainbow", "map"}:
                raise ValueError(unsupported_intent_error(intent, "submit_query", "get_report()"))
            else:
                raise ValueError(invalid_intent_error(intent, {"count", "table", "sources"}, "submit_query"))

        taxa = identifiers_output.get("taxa", [])
        assemblies = identifiers_output.get("assemblies", [])
        samples = identifiers_output.get("samples", [])
        taxon_filter_type = identifiers_output.get("taxon_filter_type", "children")
        rank = identifiers_output.get("rank")
        user_query = identifiers_output.get("user_query", "unknown")

        show_table = intent == "table"
        show_sources = intent == "sources"

        if show_table:
            if size is None:
                size = 10  # Default size for tables
            if sort_by:
                try:
                    sort_by = sort_by.split(" ")[0].split(".")[0].split(":")[0]
                    await fetch_valid_types(search_index)
                    validate_attribute_name(sort_by, search_index, FIELD_CACHE)
                except ValueError as ve:
                    raise ValueError(
                        f"""Error in sort_by attribute validation: {str(ve)}"""
                    ) from ve

        attributes = attributes_output.get("attributes", [])
        fields = attributes_output.get("fields", [])
        names = attributes_output.get("names", [])
        ranks = attributes_output.get("ranks", [])

        # Import here to avoid circular dependency
        from .search import advanced_search

        # Delegate to advanced_search with the parsed components
        result = await advanced_search(
            user_query=user_query,
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
            show_table=show_table,
            show_sources=show_sources,
            size=size if show_table else None,
            sort_by=sort_by if show_table else None,
            sort_order=sort_order if show_table else None,
            page=page if show_table else None,
        )

        # Extract top-level fields from advanced_search result
        count = result.get("count", 0)
        url = result.get("url", "")
        results = result.get("results", []) if show_table else []

        # Build response envelope - always returns consistent structure
        response_envelope = {
            "user_query": user_query,
            "search_tips": set_search_tips(attributes, fields, intent),
            "count": count,
            "url": url,
            "search_index": search_index,
        }

        # Include raw results for table intent
        if show_table:
            response_envelope["results"] = []

        # Conditionally include formatted output based on response_format
        if count > 0 and show_table and results:
            processed_table = process_result_table(
                results,
                search_fields=fields or [],
                search_names=names or [],
                search_ranks=ranks or [],
            )
            response_envelope["results"] = processed_table

            if response_format in {"markdown", "full"}:
                response_envelope["markdown"] = format_result_table(
                    processed_table=processed_table,
                    search_url=url,
                    format="markdown",
                )

            if response_format in {"csv", "full"}:
                response_envelope["csv"] = format_result_table(
                    processed_table=processed_table,
                    search_url=url,
                    format="csv",
                )

            if response_format == "full":
                # Placeholder for sources implementation
                response_envelope["sources"] = []
        else:
            # No results to format
            if response_format in {"markdown", "full"}:
                response_envelope["markdown"] = ""
            if response_format in {"csv", "full"}:
                response_envelope["csv"] = ""

        # Log successful call
        duration_ms = (time.time() - start) * 1000
        log_tool_usage(
            tool_name="submit_query",
            params={
                "intent": intent,
                "search_index": search_index or "default",
                "identifiers_artifact_id": identifiers_artifact_id,
                "attributes_artifact_id": attributes_artifact_id,
                "response_format": response_format,
            },
            duration_ms=duration_ms,
            success=True,
            result_summary={
                "count": count,
                "has_results": show_table and bool(results),
                "response_format": response_format,
            }
        )

        return response_envelope

    except ToolExecutionError as e:
        duration_ms = (time.time() - start) * 1000
        log_tool_usage(
            tool_name="submit_query",
            params={
                "intent": intent,
                "search_index": search_index or "default",
                "identifiers_artifact_id": identifiers_artifact_id,
                "attributes_artifact_id": attributes_artifact_id,
                "response_format": response_format,
            },
            duration_ms=duration_ms,
            success=False,
            error=str(e)
        )

        return {
            "user_query": user_query or "unknown",
            "error": e.message,
            "error_type": "handled",
            "error_tool": e.tool_name,
        }

    except Exception as e:
        # Log error
        duration_ms = (time.time() - start) * 1000
        logger.exception("Unexpected error in submit_query")
        log_tool_usage(
            tool_name="submit_query",
            params={
                "intent": intent,
                "search_index": search_index or "default",
                "identifiers_artifact_id": identifiers_artifact_id,
                "attributes_artifact_id": attributes_artifact_id,
                "response_format": response_format,
            },
            duration_ms=duration_ms,
            success=False,
            error=str(e)
        )

        # Format error for user with issue reporting guidance
        issue_info = format_unhandled_error_for_issue("submit_query", str(e))
        return {
            "user_query": user_query or "unknown",
            "error": issue_info["user_message"],
            "error_type": "unhandled",
            "issue_url": issue_info["issue_url"],
            "issue_create_url": issue_info["issue_create_url"],
        }


# Set the __doc__ to SUBMIT_QUERY_PROMPT so the LLM sees detailed instructions and examples,
# not the developer-focused docstring above.
submit_query.__doc__ = SUBMIT_QUERY_PROMPT


def register_tools(mcp) -> None:
    """Register query parser tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(submit_query)
