import time
from typing import Any

from ..logging_config import get_logger
from .helpers.api import make_goat_request
from .helpers.constants import GOAT_API_BASE, GOAT_DESCRIPTION

logger = get_logger(__name__)
FIELD_CACHE: dict[str, Any] = {}
_FIELD_CACHE_TIMESTAMP: dict[str, float] = {}
_FIELD_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


async def _fetch_valid_types(search_index: str = "taxon") -> dict[str, Any]:
    """Internal function to fetch valid attribute types from GoaT API.

    Uses in-memory cache with 24-hour TTL to avoid repeated API calls.

    Args:
        search_index: Index type (default: taxon)
    """
    global FIELD_CACHE, _FIELD_CACHE_TIMESTAMP
    # Check if we have a valid cached response
    current_time = time.time()
    if search_index in FIELD_CACHE and search_index in _FIELD_CACHE_TIMESTAMP:
        cache_age = current_time - _FIELD_CACHE_TIMESTAMP[search_index]
        if cache_age < _FIELD_CACHE_TTL_SECONDS:
            return FIELD_CACHE[search_index]

    # Cache miss or expired - fetch from API
    url = f"{GOAT_API_BASE}/resultFields?index={search_index}"
    data = await make_goat_request(url)
    if not data or "fields" not in data:
        return {}

    # Store in cache
    fields = data["fields"]
    FIELD_CACHE[search_index] = fields
    _FIELD_CACHE_TIMESTAMP[search_index] = current_time

    return fields


async def get_valid_types(search_index: str = "taxon") -> dict[str, Any]:
    """Fetch valid attribute types from GoaT API.

    Args:
        search_index: Index type (default: taxon)
    """
    return await _fetch_valid_types(search_index)


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


async def get_attribute_selection_context(
    keyword: str, search_index: str = "taxon"
) -> dict[str, Any]:
    """Get context information for attribute selection.

    An LLM MUST use this to choose appropriate attributes to filter by
    based on a user query. The LLM MUST always check whether an attribute
    exists before using it in a query.

    IMPORTANT: This function provides special disambiguation guidance when
    keywords suggest confusion between target lists and sequencing status.

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
    mcp.tool()(get_valid_types)
    mcp.tool()(get_metadata_for_attribute)
    mcp.tool()(get_attribute_selection_context)
