"""Guidance tool to help LLMs choose the correct attribute type."""

from ..logging_config import get_logger

logger = get_logger(__name__)


async def get_attribute_guide(query_type: str) -> str:
    """Get guidance on which attributes to use for CONFUSING query types.

    ⚠️ SCOPE: This tool ONLY handles 4 confusing cases:
    - target_list vs sequencing_status (project queries)
    - protected_status vs conservation_status

    For ALL OTHER attributes (genome_size, chromosome_number, assembly_level, etc.),
    use get_attribute_selection_context instead.

    CRITICAL: Call this when the query mentions projects like DToL, CANBP, VGP
    to avoid confusing "target list" with "sequencing status".

    Query types:
    - "target_list": For questions about which species are ON a list/project
      Example: "How many species are on the DToL target list?"
      → Use attribute: long_list with value: dtol
      → NOT sequencing_status_dtol

    - "sequencing_status": For questions about sequencing progress/stage
      Example: "How many species have completed sequencing for DToL?"
      → Use attribute: sequencing_status_dtol
      → NOT long_list

    - "protected_status": For questions about conservation/legal protection
      Example: "Which species have protected status?"
      → Use attribute: protected_status

    - "conservation_status": For questions about threat level
      Example: "Which species have endangered status?"
      → Use attribute: conservation_status

    Args:
        query_type: Type of query - choose ONE:
            - "target_list": "on the DToL list", "targeted by VGP", "on CANBP list"
            - "sequencing_status": "sequencing completed", "sequencing in progress", "data available"
            - "protected_status": "protected status", "legal protection", "endangered"
            - "conservation_status": "threat status", "conservation level"
    """
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
    if query_lower in guidance:
        return guidance[query_lower]

    return f"""Unknown query type: '{query_type}'

Valid types:
- target_list: "on the DToL list", "targeted by", "on CANBP list"
- sequencing_status: "sequencing completed", "data available", "in progress"
- protected_status: "protected", "legal protection"
- conservation_status: "endangered", "threatened", "threat level"

Call get_attribute_guide with one of these types for detailed guidance."""


def register_tools(mcp) -> None:
    """Register attribute guide tool with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(get_attribute_guide)
