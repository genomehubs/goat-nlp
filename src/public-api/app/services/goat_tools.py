"""GoaT MCP tools definition for LLM function calling"""

GOAT_TOOLS = [
    {
        "name": "goat_search_goat",
        "description": """Search GoaT database for species with genomic metadata.

Use this to answer questions about:
- How many species/taxa match criteria
- Which species have specific attributes (assemblies, chromosome data, etc.)
- Taxonomic queries within groups (mammals, plants, insects, etc.)

Examples:
- "How many plant species have chromosome data?"
- "Which mammals have chromosome-level assemblies?"
- "Count of insect species with genomes"
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_index": {
                    "type": "string",
                    "enum": ["taxon", "assembly", "sample"],
                    "description": "Index type: taxon (default), assembly, or sample",
                    "default": "taxon",
                },
                "taxon": {
                    "type": "string",
                    "description": "Taxonomic scope (e.g., 'Viridiplantae', 'Mammalia', 'Insecta')",
                },
                "rank": {
                    "type": "string",
                    "description": "Taxonomic rank filter (e.g., 'species', 'genus', 'family')",
                },
                "attributes": {
                    "type": "array",
                    "description": "Attribute filters with name, operator, value",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "operator": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                },
                "show_table": {
                    "type": "boolean",
                    "description": "Return table of results (true) or count (false)",
                    "default": False,
                },
                "size": {
                    "type": "integer",
                    "description": "Number of results if show_table is true",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
    {
        "name": "goat_get_goat_report",
        "description": """Get histogram or other reports from GoaT search results.

Use this to visualize distributions of attributes like:
- Chromosome number distributions
- Genome size ranges
- Assembly quality levels

Requires a search_url from a previous goat_search_goat call.
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_url": {
                    "type": "string",
                    "description": "GoaT search URL from previous query",
                },
                "report_type": {
                    "type": "string",
                    "enum": ["histogram", "sources", "scatter", "tree"],
                    "description": "Type of report",
                    "default": "histogram",
                },
                "rank": {
                    "type": "string",
                    "description": "Taxonomic rank for histogram/scatter",
                },
            },
            "required": ["search_url"],
        },
    },
    {
        "name": "goat_get_attribute_selection_context",
        "description": """Find valid attribute names in GoaT for filtering.

Use this when you need to discover what attributes are available
for a specific topic (e.g., "chromosome", "assembly", "genome size").

Always call this before using attributes in goat_search_goat.
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword for attribute discovery",
                },
                "search_index": {
                    "type": "string",
                    "enum": ["taxon", "assembly", "sample"],
                    "description": "Index type",
                    "default": "taxon",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "goat_check_taxon_exists",
        "description": """Validate a taxonomic name exists in GoaT.

Use this to check scientific names before searching.
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Scientific taxon name to check",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "goat_get_goat_record",
        "description": """Get detailed information about a specific taxon/assembly/sample.

Use this to fetch complete data for a known record ID.
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "string",
                    "description": "Record ID (taxon ID, assembly accession, sample ID)",
                },
                "search_index": {
                    "type": "string",
                    "enum": ["taxon", "assembly", "sample"],
                    "description": "Index type",
                },
                "attributes": {
                    "type": "array",
                    "description": "Specific attributes to include",
                    "items": {"type": "string"},
                },
            },
            "required": ["record_id", "search_index"],
        },
    },
]


def get_tools_for_provider(provider: str) -> list:
    """Convert GoaT tools to provider-specific format"""
    if provider == "anthropic":
        return GOAT_TOOLS
    elif provider == "openai":
        # Convert to OpenAI function calling format
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in GOAT_TOOLS
        ]
    elif provider == "google":
        # Google uses the same format as Anthropic (MCP standard)
        return GOAT_TOOLS
    return GOAT_TOOLS
