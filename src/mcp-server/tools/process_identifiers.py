"""Process identifiers tool for preparing identifier-related query parameters."""

from typing import Any

from ..logging_config import get_logger
from .helpers.validation import hash_dict

logger = get_logger(__name__)

PROCESS_IDENTIFIERS_PROMPT = """Process and validate identifier-related query parameters for GoaT API queries.

Follow the procedure below to extract and format the identifiers correctly. Ignore any other information, this
will be handled in a subsequent step.

IMPORTANT: values passed to taxa MUST be valid SCIENTIFIC NAMES or IDs.
You can check taxon names using check_taxon_exists() if needed.

FOLLOW THESE STEPS EXACTLY:

1. **Identify the ID TYPE and extract it**:
   - TAXA (species/families/genera): Translate organism names
     Examples: "mammal"→"Mammalia", "cat"→"Felis", "dog"→"Canis"
     Pass as: taxa="Mammalia" OR as a list, e.g. taxa=["Felis", "Canis"]
     If no taxa are mentioned, pass an empty list: taxa=[]

   - ASSEMBLIES (genome): Extract accession like "GCF_000002305.6"
     Pass as: assemblies="GCF_000002305.6" OR as a list, e.g. assemblies=["GCF_000002305.6", "GCA_000001405.28"]
     If no assemblies are mentioned, pass an empty list: assemblies=[]

   - SAMPLES (DNA/RNA): Extract accession like "SRR1234567"
     Pass as: samples="SRR1234567" OR as a list, e.g. samples=["SRR1234567", "SRR7654321"]
     If no samples are mentioned, pass an empty list: samples=[]

2. **rank** (if applicable): The taxonomic rank
   Examples: "species", "family", "genus", "order"
   If no rank is mentioned, pass as: rank=""

3. **taxon_filter_type**: Type of taxon filter to apply if taxa provided
   Options:
   - "children" (default): e.g. "families in Felis"
   - "matching": e.g. "matching Canis*", "for Nymphalidae"
   - "lineage": e.g. "lineage of Mammalia", "parent taxa of Felis"

4. **intent**: What kind of result
   - "count": "How many..." (count species; default)
   - "table": "Which...", "List..." (show results)

5. **user_query**: Copy the original question EXACTLY. DO NOT MODIFY IT.

TAXON NAME TRANSLATIONS:
mammal→Mammalia, cat→Felis, dog→Canis, bat→Chiroptera,
bird→Aves, primate→Primates, fish→Actinopterygii,
insect→Insecta, plant→Plantae

EXAMPLE:
Query: "How many mammal species have minimum directly measured genome size < 3G?"

Step 1: ID TYPE → "mammal" = taxa → ["Mammalia"]
Step 2: Rank → "species"
Step 3: taxon_filter_type → "children"
Step 4: Intent → "How many" = "count"
Step 5: user_query → Copy exactly
THEN CALL:
process_identifiers(
  user_query="How many mammal species have minimum directly measured genome size < 3G?",
  taxa=["Mammalia"],
  rank="species",
  intent="count",
  taxon_filter_type="children"
)

DO NOT CALL unless you've completed all 5 steps above!
"""


async def set_search_index(
    taxa: list[str] | None,
    assemblies: list[str] | None,
    samples: list[str] | None,
    user_query: str
) -> None:
    """Set the search index for validation purposes.

    Args:
        taxa: List of taxon names or IDs
        assemblies: List of assembly accessions
        samples: List of sample accessions
        user_query: The original user question
    """
    search_index = None

    if assemblies:
        search_index = "assembly"
    elif samples:
        search_index = "sample"
    elif taxa:
        search_index = "taxon"
    else:
        # Try to infer from query
        from .utilities import choose_search_index
        search_index = await choose_search_index(user_query)
        logger.info(f"Inferred search_index from query: {search_index}")
    return search_index


async def process_identifiers(
    user_query: str,
    taxa: list[str] | None = None,
    assemblies: list[str] | None = None,
    samples: list[str] | None = None,
    rank: str | None = None,
    intent: str = "count",
    taxon_filter_type: str = "children",
) -> dict[str, Any]:
    """Process and validate identifier-related query parameters.

    Args:
        user_query: The original user question
        taxa: List of taxon names or IDs
        assemblies: List of assembly accessions
        samples: List of sample accessions
        rank: Taxonomic rank if applicable
        intent: Result type - "count" (default), "table", "histogram", or "record"
        taxon_filter_type: Type of taxon filter to apply if taxa provided
                           Options: "children" (default), "matching", "lineage"

    Returns:
        A dictionary with processed identifiers for GoaT API queries.
"""
    if taxa is None:
        taxa = []
    elif isinstance(taxa, str):
        taxa = [taxa]
    if assemblies is None:
        assemblies = []
    elif isinstance(assemblies, str):
        assemblies = [assemblies]
    if samples is None:
        samples = []
    elif isinstance(samples, str):
        samples = [samples]
    search_index = await set_search_index(taxa, assemblies, samples, user_query)
    if not search_index:
        raise ValueError("Could not determine search_index in process_identifiers().")
    result: dict[str, Any] = {
        "taxa": taxa,
        "assemblies": assemblies,
        "samples": samples,
        "rank": rank if rank is not None else "",
        "intent": intent,
        "taxon_filter_type": taxon_filter_type,
        "search_index": search_index,
        "user_query": user_query,
    }

    dict_hash = hash_dict(result)

    result["unique_id"] = dict_hash

    return result


process_identifiers.__doc__ = PROCESS_IDENTIFIERS_PROMPT


def register_tools(mcp) -> None:
    """Register process identifiers tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(process_identifiers)
