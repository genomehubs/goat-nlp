import re

from ...logging_config import get_logger

logger = get_logger(__name__)


def infer_index_from_query(query: str) -> dict[str, str]:
    """Infer the most appropriate search index based on the user query.

    This function analyzes the user query to determine whether it is most
    relevant to the "taxon", "assembly", or "sample" search index. It uses
    keyword detection and contextual clues to make this inference.

    Args:
        query: The original user query as a string.

    Returns:
        dict with keys: search_index (one of "taxon", "assembly", "sample"),
        reasoning (explanation of choice)
    """
    query_lower = query.lower()

    # Look for what is being counted/listed
    # Assembly index: explicitly counting assemblies
    # Patterns for assembly index, including those with words between "how many"/"count"/etc. and "assemblies"
    assembly_patterns = [
        "how many assemblies",
        "count assemblies",
        "list assemblies",
        "which assemblies",
        "show assemblies",
        "assemblies for",
        "assemblies with",
    ]

    # Regex patterns to catch phrases like "how many ___ assemblies", "count the ___ assemblies", etc.
    assembly_regexes = [
        r"how many\s+\w+(?:\s+\w+){0,5}?\s+assemblies",  # up to 5 words between
        r"count(?: the)?\s+\w+(?:\s+\w+){0,5}?\s+assemblies",
        r"list(?: the)?\s+\w+(?:\s+\w+){0,5}?\s+assemblies",
        r"which\s+\w+(?:\s+\w+){0,5}?\s+assemblies",
        r"show(?: me)?(?: the)?\s+\w+(?:\s+\w+){0,5}?\s+assemblies",
    ]
    if any(pattern in query_lower for pattern in assembly_patterns):
        return {"search_index": "assembly", "reasoning": "Query explicitly asks about counting or listing assemblies"}
    if any(re.search(regex, query_lower) for regex in assembly_regexes):
        return {"search_index": "assembly", "reasoning": "Query contains pattern indicating assembly-level counting"}
    if any(pattern in query_lower for pattern in assembly_patterns):
        return {"search_index": "assembly", "reasoning": "Query contains pattern indicating assembly-level counting"}

    # Sample index: explicitly counting samples
    sample_patterns = [
        "how many samples",
        "count samples",
        "list samples",
        "which samples",
        "show samples",
        "samples for",
        "samples with",
    ]
    if any(pattern in query_lower for pattern in sample_patterns):
        return {"search_index": "sample", "reasoning": "Query explicitly asks about counting or listing samples"}
    # Regex patterns to catch phrases like "how many ___ samples", "count the ___ samples", etc.
    sample_regexes = [
        r"how many\s+\w+(?:\s+\w+){0,5}?\s+samples",  # up to 5 words between
        r"count(?: the)?\s+\w+(?:\s+\w+){0,5}?\s+samples",
        r"list(?: the)?\s+\w+(?:\s+\w+){0,5}?\s+samples",
        r"which\s+\w+(?:\s+\w+){0,5}?\s+samples",
        r"show(?: me)?(?: the)?\s+\w+(?:\s+\w+){0,5}?\s+samples",
    ]
    if any(re.search(regex, query_lower) for regex in sample_regexes):
        return {"search_index": "sample", "reasoning": "Query contains pattern indicating sample-level counting"}

    return {
        "search_index": "taxon",
        "reasoning": (
            "Leave search_index setting to LLM/user judgement based on query and "
            "intent, but default to taxon index if uncertain"
        ),
    }


def resolve_index(
    search_index: str,
    identifiers_output: dict,
    attributes_output: dict,
) -> str:
    """Determine the search index to use based on provided identifiers and attributes."""
    attr_index = attributes_output.get("search_index", {})
    if attr_index and isinstance(attr_index, dict):
        attr_index = attr_index.get("search_index")
    id_index = identifiers_output.get("search_index", {})
    if id_index and isinstance(id_index, dict):
        id_index = id_index.get("search_index")

    if search_index is not None:
        resolved_index = search_index
        source = "arg"
    elif attr_index:
        resolved_index = attr_index
        source = "attributes_artifact"
    elif id_index:
        resolved_index = id_index
        source = "identifiers_artifact"
    else:
        resolved_index = "taxon"
        source = "default"

    if attr_index and search_index and attr_index != search_index:
        raise ValueError(f"search_index mismatch: attributes={attr_index}, submit_query={search_index}")
    if id_index and search_index and id_index != search_index:
        raise ValueError(f"search_index mismatch: identifiers={id_index}, submit_query={search_index}")

    search_index = resolved_index
    logger.info("search_index resolved to '%s' from %s", search_index, source)

    return search_index
