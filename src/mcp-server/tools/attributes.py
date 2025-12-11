from typing import Any

from ..logging_config import get_logger
from .helpers.constants import GOAT_DESCRIPTION
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
) -> dict[str, Any]:
    """Get metadata for a specific attribute in GoaT.

    ONLY use this to get detailed information about a single attribute,
    such as its description, type, and possible values. If you are unsure if an attribute exists or
    which attributes to use for filtering, use get_attribute_selection_context().

    DO NOT use this tool to guess attribute names or validate multiple attributes at once.

    Args:
        attribute: Name of the attribute to get metadata for
        search_index: Index type (default: taxon)
    """
    fields = await fetch_valid_types(search_index)
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
    valid_names = {
        "scientific name": "scientific_name",
        "common name": "common_name",
        "synonym": "synonym",
        "tolid prefix": "tolid_prefix",
        "tolid": "tolid_prefix",
        "authority": "authority"}
    fields = await fetch_valid_types(search_index)
    if not fields:
        return {}

    # Split keyword into individual words for matching
    keyword_lower = keyword.lower()
    keyword_words = set(keyword_lower.replace("_", " ").split())

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
            attr_info = {"name": name, "name_type": "attribute", **field}
            attributes.append(attr_info)
        # If no phrase match, check if any individual words match
        elif keyword_words and any(word in search_text for word in keyword_words if len(word) > 2):
            attr_info = {"name": name, "name_type": "attribute", **field}
            attributes.append(attr_info)

    # Also check valid names
    if keyword_lower.replace("_", " ") in valid_names:
        attr_info = {"name": valid_names[keyword_lower.replace("_", " ")], "name_type": "name"}
        attributes.append(attr_info)

    # Also check valid ranks
    valid_ranks = await fetch_valid_ranks()
    logger.info(f"Checking keyword '{keyword_lower}' against valid ranks: {valid_ranks}")
    if keyword_lower in (rank.lower() for rank in valid_ranks):
        attr_info = {"name": keyword_lower, "name_type": "rank"}
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


async def get_attribute_selection_context(
    keyword: str, search_index: str = "taxon"
) -> dict[str, Any]:
    """Get context information for attribute selection.

    An LLM MUST use this to choose appropriate attributes to filter by
    based on a user query. The LLM MUST always check whether an attribute
    exists before using it in a query.

    The LLM must check the returned 'name_type' for each attribute to
    determine whether it is an 'attribute', a 'name', or a 'rank'.

    IMPORTANT: This function provides special disambiguation guidance when
    keywords suggest confusion between target lists and sequencing status.

    IMPORTANT: If you do not get results with a keyword search, try different
    keywords or use a descriptive phrase to expand your search.

    Args:
        keyword: Keyword to guide attribute selection
        search_index: Index type (default: taxon)
    """
    logger.info(f"get_attribute_selection_context called: keyword='{keyword}', search_index={search_index}")

    # Check for keywords that need disambiguation guidance
    keyword_lower = keyword.lower()
    disambiguation_guidance = None

    # Detect project-related queries that might confuse target_list vs sequencing_status
    project_keywords = ["dtol", "canbp", "vgp", "ebp", "project", "target", "list", "long_list"]
    status_keywords = ["sequencing", "status", "progress", "completed", "data", "available"]

    has_project_keyword = any(kw in keyword_lower for kw in project_keywords)
    has_status_keyword = any(kw in keyword_lower for kw in status_keywords)

    if has_project_keyword or has_status_keyword:
        disambiguation_guidance = """
⚠️  DISAMBIGUATION GUIDANCE - Read this first!

If asking which species are ON a target list:
  → Use: long_list attribute
  → Values: dtol, canbp, vgp, ebp, etc.
  → Example: "How many species are on the DToL target list?" → long_list=dtol

If asking about sequencing STATUS/PROGRESS:
  → Use: sequencing_status_dtol, sequencing_status_canbp, etc.
  → Values: completed, in_progress, planned, etc.
  → Example: "How many species have completed sequencing for DToL?" → sequencing_status_dtol=completed

Common confusion:
  ✗ WRONG: "species on dtol list" → sequencing_status_dtol
  ✓ RIGHT: "species on dtol list" → long_list=dtol

  ✗ WRONG: "species with completed dtol sequencing" → long_list=dtol
  ✓ RIGHT: "species with completed dtol sequencing" → sequencing_status_dtol=completed
"""

    # Detect protected/conservation status queries
    if "protected" in keyword_lower or "conservation" in keyword_lower:
        disambiguation_guidance = """
⚠️  DISAMBIGUATION GUIDANCE - Read this first!

For legal protection status:
  → Use: protected_status attribute
  → Example: "Which species have protected status?"

For threat/conservation level:
  → Use: conservation_status attribute
  → Example: "Which species are endangered?"
"""

    result = await _get_attribute_context_internal(keyword, search_index)

    # Add disambiguation guidance at the top of the result if present
    if disambiguation_guidance:
        result = {
            "IMPORTANT_READ_FIRST": disambiguation_guidance,
            **result
        }

    logger.info(f"Found {len(result.get('attributes', []))} matching attributes")
    return result


def register_tools(mcp) -> None:
    """Register GoaT attribute tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    # mcp.tool()(get_valid_types)
    mcp.tool()(get_metadata_for_attribute)
    mcp.tool()(get_attribute_selection_context)
