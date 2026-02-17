"""Process identifiers tool for preparing identifier-related query parameters."""

from typing import Any

from ..config import DATASTORE_NAME
from ..logging_config import get_logger
from .helpers.normalisation import normalise_to_list
from .helpers.processor_common import finalise_and_store
from .helpers.validation import validate_prefixes

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

  If an identifier does not match any of the above types, consider that it may be an attribute that should be 
  processed with process_attributes() instead.

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
    # Normalise all inputs to lists
    taxa = normalise_to_list(taxa)
    assemblies = normalise_to_list(assemblies)
    samples = normalise_to_list(samples)

    if taxa and not validate_prefixes(taxa, "taxa"):
        raise ValueError("Taxa identifiers must be valid scientific names or IDs.")
    if assemblies and not validate_prefixes(assemblies, "assemblies"):
        raise ValueError("Assembly identifiers must be valid accessions like GCF_000002305.6.")
    if samples and not validate_prefixes(samples, "samples"):
        raise ValueError("Sample identifiers must be valid accessions like SRR1234567.")

    # Clean and encode taxa (handle exclamation marks for NOT filters)
    taxa = [t.strip().replace("!", "%21") for t in taxa if t.strip() != ""]

    result: dict[str, Any] = {
        "taxa": taxa,
        "assemblies": assemblies,
        "samples": samples,
        "rank": rank if rank is not None else "",
        "taxon_filter_type": taxon_filter_type,
        "user_query": user_query,
    }

    return finalise_and_store(result)


process_identifiers.__doc__ = PROCESS_IDENTIFIERS_PROMPT


def register_tools(mcp) -> None:
    """Register process identifiers tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """
    mcp.tool()(process_identifiers)


if __name__ == "__main__":
    import asyncio

    from .artifact_store import retrieve

    async def test_process_identifiers():
        """Test examples for process_identifiers."""
        print("=" * 60)
        print("Testing process_identifiers")
        print("=" * 60)

        # Test 1: Basic taxa query
        print("\n[Test 1] Basic taxa query")
        result1 = await process_identifiers(
            user_query="How many mammal species are there?",
            taxa=["Mammalia"],
            rank="species",
            taxon_filter_type="children"
        )
        print(f"  Artifact ID: {result1['artifact_id']}")
        data1 = retrieve(result1['artifact_id'])
        print(f"  Taxa: {data1['taxa']}")
        print(f"  Rank: {data1['rank']}")
        print(f"  Filter type: {data1['taxon_filter_type']}")
        print(f"  Unique ID: {data1['unique_id'][:16]}...")

        # Test 2: Multiple taxa with NOT filter
        print("\n[Test 2] Multiple taxa with NOT filter")
        result2 = await process_identifiers(
            user_query="Species in Mammalia excluding Felis",
            taxa=["Mammalia", "!Felis"],
            rank="species"
        )
        print(f"  Artifact ID: {result2['artifact_id']}")
        data2 = retrieve(result2['artifact_id'])
        print(f"  Taxa (with NOT): {data2['taxa']}")
        print(f"  Note: '!' encoded as '%21': {data2['taxa'][1]}")

        # Test 3: String normalisation (single string instead of list)
        print("\n[Test 3] String normalisation")
        result3 = await process_identifiers(
            user_query="Get assembly GCF_000002305.6",
            assemblies="GCF_000002305.6"  # String, not list
        )
        print(f"  Artifact ID: {result3['artifact_id']}")
        data3 = retrieve(result3['artifact_id'])
        print(f"  Assemblies: {data3['assemblies']}")
        print(f"  Type: {type(data3['assemblies'])}")

        # Test 4: None normalisation
        print("\n[Test 4] None normalisation")
        result4 = await process_identifiers(
            user_query="Count all species",
            rank="species"
            # taxa, assemblies, samples all None
        )
        print(f"  Artifact ID: {result4['artifact_id']}")
        data4 = retrieve(result4['artifact_id'])
        print(f"  Taxa: {data4['taxa']} (empty list from None)")
        print(f"  Assemblies: {data4['assemblies']}")
        print(f"  Samples: {data4['samples']}")

        # Test 5: Wildcard and lineage filter
        print("\n[Test 5] Wildcard and lineage filter")
        result5 = await process_identifiers(
            user_query="Lineage of Canis*",
            taxa="Canis*",
            taxon_filter_type="lineage"
        )
        print(f"  Artifact ID: {result5['artifact_id']}")
        data5 = retrieve(result5['artifact_id'])
        print(f"  Taxa: {data5['taxa']}")
        print(f"  Filter type: {data5['taxon_filter_type']}")

        # Test 6: Hash consistency check
        print("\n[Test 6] Hash consistency (same input = same hash)")
        result6a = await process_identifiers(
            user_query="Test",
            taxa=["Mammalia"],
            rank="species"
        )
        result6b = await process_identifiers(
            user_query="Test",
            taxa=["Mammalia"],
            rank="species"
        )
        data6a = retrieve(result6a['artifact_id'])
        data6b = retrieve(result6b['artifact_id'])
        print(f"  Hash A: {data6a['unique_id'][:16]}...")
        print(f"  Hash B: {data6b['unique_id'][:16]}...")
        print(f"  Hashes match: {data6a['unique_id'] == data6b['unique_id']}")

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)

    asyncio.run(test_process_identifiers())
