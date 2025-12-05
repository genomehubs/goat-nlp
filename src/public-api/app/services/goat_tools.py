"""GoaT MCP tools definition for LLM function calling"""

GOAT_TOOLS = [
    {
        "name": "goat_query",
        "description": """🔬 RECOMMENDED: Parse-based approach for GoaT queries.

Extract structured components from user questions. Backend handles GoaT API details.

Extract these components:
1. **taxon**: For species/families/genera queries (e.g., "Mammalia", "Felis")
2. **assembly**: For genome assembly queries (e.g., "GCF_000002305.6")
3. **sample**: For sample queries (e.g., "SRR1234567")
4. **rank**: Taxonomic rank (species, genus, family, etc.)
5. **attributes**: List of attribute filters with optional modifiers
6. **intent**: "count", "table", "histogram", or "record"

Modifiers for attributes (can be string or list):
- "missing": Records WITHOUT this attribute
- "direct": Directly measured only
- ["min", "direct"]: Combine summary + status modifiers

Examples:
Q: "How many mammal species have minimum directly measured genome size < 3G?"
→ intent="count", taxon="Mammalia", rank="species",
  attributes=[{"name": "genome_size", "modifier": ["min", "direct"], "operator": "<", "value": "3G"}]

Q: "Tell me about assembly GCF_000002305.6"
→ intent="record", assembly="GCF_000002305.6"
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_query": {
                    "type": "string",
                    "description": "Original question (required for backend processing)",
                },
                "taxon": {
                    "type": "string",
                    "description": (
                        "Scientific name or taxon ID for species/families/genera queries "
                        "(e.g., 'Mammalia', 'Felis', '9615')"
                    ),
                },
                "assembly": {
                    "type": "string",
                    "description": "Assembly accession for assembly queries (e.g., 'GCF_000002305.6')",
                },
                "sample": {
                    "type": "string",
                    "description": "Sample accession for sample queries (e.g., 'SRR1234567')",
                },
                "rank": {
                    "type": "string",
                    "description": "Taxonomic rank: species, genus, family, etc. (for taxon queries)",
                },
                "attributes": {
                    "type": "array",
                    "description": "Attribute filters with optional modifiers",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "operator": {"type": "string"},
                            "value": {"type": "string"},
                            "modifier": {
                                "description": "Single modifier (string) or combined modifiers (array)",
                                "oneOf": [
                                    {
                                        "type": "string",
                                        "enum": [
                                            "missing",
                                            "direct",
                                            "ancestral",
                                            "estimated",
                                            "min",
                                            "max",
                                            "median",
                                            "length",
                                        ],
                                    },
                                    {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "enum": [
                                                "missing",
                                                "direct",
                                                "ancestral",
                                                "estimated",
                                                "min",
                                                "max",
                                                "median",
                                                "length",
                                            ],
                                        },
                                    },
                                ],
                            },
                        },
                    },
                },
                "intent": {
                    "type": "string",
                    "description": "Result type: count, table, histogram, record, report",
                    "enum": ["count", "table", "histogram", "record", "report"],
                    "default": "count",
                },
            },
            "required": ["user_query"],
        },
    },
    {
        "name": "goat_simple_search",
        "description": """Simple search interface for common GoaT queries.

Use this for straightforward questions about genomic data.
Perfect for counting species, families, assemblies, or samples.

Examples:
- "How many cat species have genome size data?"
- "Which bat families are targeted by VGP?"
- "How many species have a tolid prefix beginning ilLys?"

Parameters:
- user_query: Your original question (required)
- what_to_count: What you're counting (species, families, genera, orders, assemblies, samples)
- taxon: Scientific name for taxonomic scope (optional)
  Common names: mammals→Mammalia, cats→Felis, dogs→Canis, bats→Chiroptera, birds→Aves, insects→Insecta
- specific_attribute: Attribute name to filter by (optional)
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_query": {
                    "type": "string",
                    "description": "The original user question (required)",
                },
                "what_to_count": {
                    "type": "string",
                    "description": "What you're counting: species, families, genera, orders, assemblies, samples",
                    "enum": [
                        "species",
                        "genus",
                        "genera",
                        "family",
                        "families",
                        "order",
                        "orders",
                        "class",
                        "classes",
                        "phylum",
                        "phyla",
                        "kingdom",
                        "assemblies",
                        "assembly",
                        "samples",
                        "sample",
                    ],
                },
                "taxon": {
                    "type": "string",
                    "description": "Scientific name for taxonomic scope (e.g., 'Mammalia', 'Felis', 'Chiroptera')",
                },
                "specific_attribute": {
                    "type": "string",
                    "description": "Attribute name to filter by (e.g., 'genome_size', 'assembly_level')",
                },
            },
            "required": ["user_query"],
        },
    },
    {
        "name": "goat_advanced_search",
        "description": """Advanced search interface for complex GoaT queries.

Use this for complex queries with multiple filters or specific attribute requirements.
For most simple queries, use goat_simple_search instead.

Examples:
- "Which species are on BOTH DToL and CANBP lists?" (AND logic)
- "Count species with either high genome size OR high chromosome count" (OR logic)
- "Species missing genome data but with assembly info" (exclusions)
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
                "user_query": {
                    "type": "string",
                    "description": "The original user question (required)",
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
            "required": ["user_query"],
        },
    },
    {
        "name": "goat_get_goat_report",
        "description": """Get histogram or other reports from GoaT search results.

Use this to visualize distributions of attributes like:
- Chromosome number distributions
- Genome size ranges
- Assembly quality levels

Requires a search_url from a previous goat_advanced_search call.
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
        "description": """Find valid attribute names in GoaT with built-in disambiguation guidance.

Use this to discover attributes for any keyword. Provides automatic guidance for confusing cases:

⚠️ AUTOMATIC DISAMBIGUATION for projects (DToL, CANBP, VGP):
- "dtol list" → Suggests long_list=dtol (target list membership)
- "dtol sequencing" → Suggests sequencing_status_dtol (sequencing progress)

For other topics, returns matching attributes:
- "genome size" → finds genome_size, genome_size_raw
- "chromosome" → finds chromosome_number, haploid_number
- "assembly" → finds assembly_level, assembly_span

This is your ONE tool for all attribute discovery.
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
