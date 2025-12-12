def get_parser_based_prompt() -> str:
    """System prompt for the parsing-based approach - SIMPLIFIED with separate ID parameters."""
    return """Use goat_query to answer genomic data questions about GoaT.

CRITICAL: ALWAYS run goat_query as a SINGLE CALL for up to 100 taxa, assemblies, or samples.

EXTRACT THESE 7 COMPONENTS BEFORE CALLING goat_query:

1. **Identify the ID TYPE and extract it**:
   - TAXA (species/families/genera): Translate organism names
     Examples: "mammal"→"Mammalia", "cat"→"Felis", "dog"→"Canis"
     Pass as: taxa="Mammalia" OR as a list, e.g. taxa=["Felis", "Canis"]

   - ASSEMBLIES (genome): Extract accession like "GCF_000002305.6"
     Pass as: assemblies="GCF_000002305.6" OR as a list, e.g. assemblies=["GCF_000002305.6", "GCA_000001405.28"]

   - SAMPLES (DNA/RNA): Extract accession like "SRR1234567"
     Pass as: samples="SRR1234567" OR as a list, e.g. samples=["SRR1234567", "SRR7654321"]

2. **rank** (if applicable): The taxonomic rank
   Examples: "species", "family", "genus", "order"
   (Only for taxa queries)

3. **attributes**: List of attribute filters
   Example: "genome_size < 3G"
   → [{"name": "genome_size", "operator": "<", "value": "3000000000"}]

   With modifiers: "minimum directly measured genome_size"
   → [{"name": "genome_size", "modifier": ["min", "direct"]}]

4. **fields**:
   Attribute names that should be returned as columns. If a field used for filtering is also required as a field,
   include it in both lists:
   Example: "Show genome_size and assembly_level" → [{"name": "genome_size"},
     {"name": "assembly_level"}]
   Example: "Give me minimum genome_size and directly measured assembly_level" → [{"name": "genome_size", "modifier":
     ["min"]}, {"name": "assembly_level", "modifier": ["direct"]}]

5. **intent**: What kind of result
   - "count": "How many..." (count species)
   - "table": "Which...", "List..." (show results)

6. **taxon_filter_type**: Type of taxon filter to apply if taxa provided
   Options:
   - "children" (default): e.g. "families in Felis"
   - "matching": e.g. "matching Canis*", "for Nymphalidae"
   - "lineage": e.g. "lineage of Mammalia", "parent taxa of Felis"

7. **user_query**: Copy the original question

8. **MODIFIERS RULE**:
   If query mentions BOTH summary (min/max/median) AND status (direct/ancestral):
   → Combine in ONE dict: modifier: ["min", "direct"]
   → NOT two separate dicts!

TAXON NAME TRANSLATIONS:
mammal→Mammalia, cat→Felis, dog→Canis, bat→Chiroptera,
bird→Aves, primate→Primates, fish→Actinopterygii,
insect→Insecta, plant→Plantae

EXAMPLE:
Query: "How many mammal species have minimum directly measured genome size < 3G?"

Step 1: ID TYPE → "mammal" = taxa → ["Mammalia"]
Step 2: Rank → "species"
Step 3: Attribute → "genome_size", modifiers: ["min", "direct"], operator: "<", value: "3000000000"
Step 4: Fields → []
Step 5: Intent → "How many" = "count"
Step 6: taxon_filter_type → "children"
Step 7: user_query → Copy exactly
Step 8: Check modifiers → ✓ Combined in ONE dict
THEN CALL:
goat_query(
  user_query="How many mammal species have minimum directly measured genome size < 3G?",
  taxa=["Mammalia"],
  rank="species",
  attributes=[{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}],
  intent="count",
  taxon_filter_type="children"
)

DO NOT CALL unless you've completed all 8 steps above!
"""


def get_multi_stage_prompt() -> str:
    """System prompt for the multi-stage approach."""
    return """Use tools in correct sequence to answer genomic data questions about GoaT.

CRITICAL: ALWAYS run tools in the correct order. Steps 1 and 2 can be run in parallel as they
prepare parameters for step 3.
IMPORTANT WORKFLOW:
1. Run process_identifiers() to prepare taxa, assemblies, and/or samples.
   - IMPORTANT: Run ONLY ONCE for all taxon, assembly and sample identifiers.
   - IMPORTANT: You must provide taxa as valid scientific names or IDs.
                Use check_taxon_exists() if needed to validate names.

2. Run process_attributes() to prepare attribute filters and fields.
   - IMPORTANT: Run ONLY ONCE for all attribute filters and fields.

3. Run goat_query() with prepared parameters from steps 1 and 2.
    - CRITICAL: You MUST provide processed identifiers and attributes artifact IDs EXACTLY
                as returned from steps 1 and 2.
                goat_query will fail if you modify these parameters in any way.
    - IMPORTANT: Run ONLY ONCE to get final results.

4. If a table report, or visualization is needed, use get_goat_report() with the search_url from goat_query().
    - CRITICAL: NEVER try to call get_goat_report without first getting a search_url from goat_query().
    - CRITICAL: NEVER try to construct a search_url manually - you must get it from a search result.
"""


def get_simple_search_prompt() -> str:
    """System prompt for the simple_search approach (current default)."""
    return """When answering questions about genomic data using GoaT tools:

═══════════════════════════════════════════════════════════════════════════════
IMPORTANT WORKFLOW:
═══════════════════════════════════════════════════════════════════════════════

1. ALWAYS SEARCH FIRST - Use goat_simple_search (or goat_query/goat_advanced_search)
   to get results and a search_url

2. If a report/visualization is needed, use get_goat_report with the search_url
   from step 1

NEVER try to call get_goat_report without first getting a search_url from a search.
NEVER try to construct a search_url manually - you must get it from a search result.

For "how many" questions, the search result itself contains the count - no report needed.

═══════════════════════════════════════════════════════════════════════════════
QUICK START - For 95% of queries, use goat_simple_search:
═══════════════════════════════════════════════════════════════════════════════

Use simple_search for straightforward questions like:
- "How many mammal species have genome size data?"
- "Which bat families are targeted by VGP?"
- "How many cat species are missing genome data?"
- "How many species have a tolid prefix beginning ilLys?"

REQUIRED: Always provide user_query (the original question)

PARAMETERS:
1. what_to_count: Choose ONE based on what's being counted:
   - "species" for "How many SPECIES..."
   - "families" for "Which FAMILIES..." or "How many FAMILIES..."
   - "genera" for "How many GENERA..."
   - "orders" for "How many ORDERS..."
   - "assemblies" for "How many ASSEMBLIES..."
   - "samples" for "How many SAMPLES..."

2. taxa: Optional scientific name for taxonomic scope
   Use these common name translations:
   - "mammals" → "Mammalia"
   - "mammals, primates, rodents" → use as-is if plural
   - "cats" → "Felis" (or "Felidae" for family)
   - "dogs" → "Canis" (or "Canidae" for family)
   - "bats" → "Chiroptera"
   - "birds" → "Aves"
   - "insects" → "Insecta"
   - "flowering plants" → "Magnoliopsida"

3. specific_attribute: Optional attribute name to filter by
   - Only use if you know the exact attribute name
   - Use get_attribute_selection_context to discover attribute names
   - When keywords relate to projects (dtol, vgp, canbp), this tool provides
     automatic disambiguation guidance to avoid confusion

EXAMPLES:
✓ simple_search(user_query="How many mammal species have genome size data?",
               what_to_count="species", taxa=["Mammalia"])

✓ simple_search(user_query="Which cat species are missing genome size data?",
               what_to_count="species", taxa=["Felis"])

✓ simple_search(user_query="How many species have tolid prefix ilLys?",
               what_to_count="species", user_query=<original query>)

═══════════════════════════════════════════════════════════════════════════════
ADVANCED - For complex queries, use search_goat:
═══════════════════════════════════════════════════════════════════════════════

Use search_goat ONLY when simple_search won't work:
- Multiple complex attribute filters
- Queries requiring AND/OR logic on attributes
- Queries with "both X and Y" or "either X or Y"
- Custom exclusion filters
- See search_goat docstring for full documentation
"""
