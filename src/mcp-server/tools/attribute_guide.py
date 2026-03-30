"""Guidance tool to help LLMs choose the correct attribute type.

Returns a structured envelope: {"guidance": str, "query_type": str}.
"""

import time

from ..logging_config import get_logger, log_tool_usage

logger = get_logger(__name__)


async def get_attribute_guide(query_type: str) -> dict[str, str]:
    """Get guidance on which attributes to use for CONFUSING query types.

    Scope: This tool handles four cases: target_list, sequencing_status,
    protected_status, conservation_status. For other attributes use
    `get_attribute_selection_context`.

    Args:
      query_type: Type of query (one of: "target_list", "sequencing_status",
            "protected_status", "conservation_status")

    Returns:
      dict with keys:
        - "guidance": guidance text
        - "query_type": canonicalized query type string
    """
    start = time.time()
    guidance = {
        "target_list": """TARGET LIST ATTRIBUTES (which species are ON a list):

Attribute name: long_list
Values: dtol, canbp, vgp, psyche, ...

Use when query asks:
✓ "How many species are ON the DToL target list?"
✓ "Which species are targeted by VGP?"
✓ "Species on both DToL AND CANBP lists?"
✓ "Count of CANBP long list species"

DO NOT use sequencing_status_dtol, sequencing_status_canbp, etc.
(Those are for sequencing progress, not list membership)
""",
        "sequencing_status": """SEQUENCING STATUS ATTRIBUTES (progress of data generation):

Attribute names: sequencing_status, sequencing_status_dtol, sequencing_status_canbp, etc.
Values: completed, in_progress, planned, ...

Use when query asks:
✓ "How many DToL species have completed sequencing?"
✓ "Species with sequencing data available?"
✓ "Count of species in sequencing progress for CANBP"

DO NOT use long_list (that's for target list membership, not progress)
""",
        "protected_status": """PROTECTED STATUS ATTRIBUTES (legal/conservation protection):

Attribute name: protected_status
Values: Yes, No, Protected, Unprotected, ...

Use when query asks:
✓ "Which species have protected status?"
✓ "Count of protected species"
✓ "Unprotected species in group X?"
""",
        "conservation_status": """CONSERVATION STATUS ATTRIBUTES (threat level):

Attribute name: conservation_status
Values: Endangered, Vulnerable, Threatened, Least Concern, ...

Use when query asks:
✓ "Which species are endangered?"
✓ "Count of threatened species"
✓ "Species with conservation concern?"
""",
    }

    query_lower = query_type.lower().strip()
    try:
        if query_lower in guidance:
            duration_ms = (time.time() - start) * 1000
            log_tool_usage(
                tool_name="get_attribute_guide",
                params={"query_type": query_type},
                duration_ms=duration_ms,
                success=True,
                result_summary={"provided": True},
            )
            return {"guidance": guidance[query_lower], "query_type": query_lower}
        msg = (
            f"Unknown query type: '{query_type}'\n\n"
            "Valid types:\n"
            "- target_list\n"
            "- sequencing_status\n"
            "- protected_status\n"
            "- conservation_status\n"
            "Call get_attribute_guide with one of these types for detailed guidance."
        )
        duration_ms = (time.time() - start) * 1000
        log_tool_usage(
            tool_name="get_attribute_guide",
            params={"query_type": query_type},
            duration_ms=duration_ms,
            success=False,
            error="unknown_query_type",
            result_summary={"provided": False},
        )
        return {"guidance": msg, "query_type": query_type}
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        log_tool_usage(
            tool_name="get_attribute_guide",
            params={"query_type": query_type},
            duration_ms=duration_ms,
            success=False,
            error=str(e),
            exc=e,
        )
        raise


def register_tools(mcp) -> None:
    """Register attribute guide tool with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(get_attribute_guide)
