GOAT_DESCRIPTION = (
    "GoaT (Genomes on a Tree): a searchable datastore of "
    "genomic and sequencing project metadata"
)


async def get_goat_description() -> str:
    """Get a description of the GoaT API."""
    return GOAT_DESCRIPTION


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


def register_resources(mcp) -> None:
    """Register GoaT resources with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register resources with
    """

    mcp.resource("resource://goat/description")(get_goat_description)
    mcp.resource("resource://goat/example-queries")(get_example_queries_resource)
