"""Process identifiers tool for preparing identifier-related query parameters."""

from typing import Any

from ..config import DATASTORE_NAME
from ..logging_config import get_logger
from .artifact_store import store
from .helpers.validation import hash_dict

logger = get_logger(__name__)

PROCESS_IDENTIFIERS_PROMPT = (
    f"""Process and validate identifier-related query parameters for """
    f"""{DATASTORE_NAME} API queries.

Follow the procedure below to extract and format the identifiers correctly. Ignore any other information, this
will be handled in a subsequent step.

If successful, this tool returns an artifact token that can be passed to submit_query().

IMPORTANT: values passed to taxa MUST be valid SCIENTIFIC NAMES or IDs.
You can check taxon names using check_taxon_exists() if needed.

Partial identifiers are allowed for taxa, assemblies, and samples using a wildcard (*) at the beginning or end.

A NOT filter can be applied to exclude specific taxa, assemblies, and samples by prefixing an exclamation mark (!).

FOLLOW THESE STEPS EXACTLY:

1. **Identify the ID TYPE and extract it**:
   - TAXA (species/families/genera): Translate organism names
     Examples: "mammal"→"Mammalia", "cat"→"Felis", "dog"→"Canis"
     Pass as: taxa="Mammalia" OR as a list, e.g. taxa=["Felis", "Canis"]
     For NOT filters, prefix with !, e.g. taxa=["Mammalia", "!Felis"]
     If no taxa are mentioned, pass an empty list: taxa=[]

   - ASSEMBLIES (genome): Extract accession like "GCF_000002305.6"
     Pass as: assemblies="GCF_000002305.6" OR as a list, e.g. assemblies=["GCF_000002305.6", "GCA_000001405.28"]
     For NOT filters, prefix with !, e.g. assemblies=["GCF_000002305.6", "!GCA_000001405.28"]
     If no assemblies are mentioned, pass an empty list: assemblies=[]

   - SAMPLES (DNA/RNA): Extract accession like "SRR1234567"
     Pass as: samples="SRR1234567" OR as a list, e.g. samples=["SRR1234567", "SRR7654321"]
     For NOT filters, prefix with !, e.g. samples=["SRR1234567", "!SRR7654321"]
     If no samples are mentioned, pass an empty list: samples=[]

2. **rank** (if applicable): The taxonomic rank
   Examples: "species", "family", "genus", "order"
   If no rank is mentioned, pass as: rank=""

3. **taxon_filter_type**: Type of taxon filter to apply if taxa provided
   Options:
   - "children" (default): e.g. "families in Mammalia", "species under Felis"
   - "matching": e.g. "matching Canis*", "for Nymphalidae"
   - "lineage": e.g. "lineage of Mammalia", "parent taxa of Felis"

4. **user_query**: Copy the original question EXACTLY. DO NOT MODIFY IT.

EXAMPLE:
Query: "How many mammal species, excluding Felis have minimum directly measured genome size < 3G?"

Step 1: ID TYPE → "mammal", "Felis" = taxa → ["Mammalia", "!Felis"]
Step 2: Rank → "species"
Step 3: taxon_filter_type → "children"
Step 4: user_query → Copy exactly
THEN CALL:
process_identifiers(
  user_query="How many mammal species, excluding Felis have minimum directly measured genome size < 3G?",
  taxa=["Mammalia", "!Felis"],
  rank="species",
  taxon_filter_type="children"
)

DO NOT CALL unless you've completed all 4 steps above!
""")


async def process_identifiers(
    user_query: str,
    taxa: list[str] | None = None,
    assemblies: list[str] | None = None,
    samples: list[str] | None = None,
    rank: str | None = None,
    taxon_filter_type: str = "children",
    search_index: str = "taxon",
) -> dict[str, Any]:
    f"""Process and validate identifier-related query parameters.

    Args:
        user_query: The original user question
        taxa: List of taxon names or IDs
        assemblies: List of assembly accessions
        samples: List of sample accessions
        rank: Taxonomic rank if applicable
        taxon_filter_type: Type of taxon filter to apply if taxa provided
                           Options: "children" (default), "matching", "lineage"
        search_index: The search index to use ("taxon", "assembly", or "sample")

    Returns:
        A dictionary with processed identifiers for {DATASTORE_NAME} API queries.
"""
    if taxa is None:
        taxa = []
    elif isinstance(taxa, str):
        taxa = [taxa]
    taxa = [t.strip().replace("!", "%21") for t in taxa if t.strip() != ""]
    if assemblies is None:
        assemblies = []
    elif isinstance(assemblies, str):
        assemblies = [assemblies]
    if samples is None:
        samples = []
    elif isinstance(samples, str):
        samples = [samples]

    result: dict[str, Any] = {
        "taxa": taxa,
        "assemblies": assemblies,
        "samples": samples,
        "rank": rank if rank is not None else "",
        "taxon_filter_type": taxon_filter_type,
        "user_query": user_query,
    }

    dict_hash = hash_dict(result)

    result["unique_id"] = dict_hash

    # Store canonical result and return an artifact token
    token = store(result)
    return {"artifact_id": token}


process_identifiers.__doc__ = PROCESS_IDENTIFIERS_PROMPT


def register_tools(mcp) -> None:
    """Register process identifiers tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(process_identifiers)
