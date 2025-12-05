"""Alternative system prompts for A/B testing different LLM approaches."""


def get_parser_based_prompt() -> str:
    """System prompt for the parsing-based approach - SIMPLIFIED with separate ID parameters."""
    return """Use goat_query to answer genomic data questions about GoaT.

EXTRACT THESE 6 COMPONENTS BEFORE CALLING goat_query:

1️⃣ **Identify the ID TYPE and extract it**:
   - TAXON (species/families/genera): Translate organism names
     Examples: "mammal"→"Mammalia", "cat"→"Felis", "dog"→"Canis"
     Pass as: taxon="Mammalia"
   
   - ASSEMBLY (genome): Extract accession like "GCF_000002305.6"
     Pass as: assembly="GCF_000002305.6"
   
   - SAMPLE (DNA/RNA): Extract accession like "SRR1234567"
     Pass as: sample="SRR1234567"

2️⃣ **rank** (if applicable): The taxonomic rank
   Examples: "species", "family", "genus", "order"
   (Only for taxon queries)

3️⃣ **attributes**: List of attribute filters
   Example: "genome_size < 3G"
   → [{"name": "genome_size", "operator": "<", "value": "3000000000"}]
   
   With modifiers: "minimum directly measured genome_size"
   → [{"name": "genome_size", "modifier": ["min", "direct"]}]

4️⃣ **intent**: What kind of result
   - "count": "How many..." (count species)
   - "table": "Which...", "List..." (show results)
   - "histogram": "Distribution of..." (show breakdown)
   - "record": "Tell me about..." (single record)

5️⃣ **user_query**: Copy the original question

6️⃣ **MODIFIERS RULE**:
   If query mentions BOTH summary (min/max/median) AND status (direct/ancestral):
   → Combine in ONE dict: modifier: ["min", "direct"]
   → NOT two separate dicts!

TAXON NAME TRANSLATIONS:
mammal→Mammalia, cat→Felis, dog→Canis, bat→Chiroptera,
bird→Aves, primate→Primates, fish→Actinopterygii,
insect→Insecta, plant→Plantae

EXAMPLE:
Query: "How many mammal species have minimum directly measured genome size < 3G?"

Step 1: ID TYPE → "mammal" = taxon → "Mammalia"
Step 2: Rank → "species"
Step 3: Attribute → "genome_size", modifiers: ["min", "direct"], operator: "<", value: "3000000000"
Step 4: Intent → "How many" = "count"
Step 5: user_query → Copy exactly
Step 6: Check modifiers → ✓ Combined in ONE dict

THEN CALL:
goat_query(
  user_query="How many mammal species have minimum directly measured genome size < 3G?",
  taxon="Mammalia",
  rank="species",
  attributes=[{"name": "genome_size", "operator": "<", "value": "3000000000", "modifier": ["min", "direct"]}],
  intent="count"
)

DO NOT CALL unless you've completed all 6 steps above!
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

2. taxon: Optional scientific name for taxonomic scope
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
               what_to_count="species", taxon="Mammalia")

✓ simple_search(user_query="Which cat species are missing genome size data?",
               what_to_count="species", taxon="Felis")

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
