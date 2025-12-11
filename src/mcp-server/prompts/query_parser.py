LLM_PROMPT_ORIGINAL = """IMPORTANT: pass the original user query string as `user_query`. The LLM MUST NOT modify this!

    Extract as many of the following parameters as possible. If a parameter is absent pass an empty list or string.

    Most importantly determine which IDs are being queried and which attributes.

    IDs can be taxon names/IDs (**taxa**), assembly accessions (**assemblies**), or sample accessions (**samples**).
    A single query can have one or two of these ID types, i.e., taxa and assemblies or taxa and samples.

    Attributes are fields to use as query filters
    For each attribute pass a dict of "name", "operator", "value", and optional "modifier"
    - Valid operators are =, !=, <, <=, >, >=, exists
    - Modifiers can be summary statistics ("min", "max", "median", "length") or status modifiers
    ("missing", "direct", "ancestral", "descendant", "estimated")
    - To combine attributes with AND logic, include multiple attribute dicts in the list.
    - To combine with OR logic, a list of keywords may be passed as the value to a single attribute.

    Fields are attribute names to return as columns in the result
    For each field pass a dict of "name" and optional "modifier"
    If an attribute used for filtering is also required as a field, include it in both lists.

    1. **taxa**: If query is about species/families/genera/orders
       - Translate common names: "mammal"→"Mammalia", "cat"→"Felis", "dog"→"Canis"
       - Each taxon name may be a prefix or partial match if the query implies it.
         Use wildcards (*) as needed.
       - Examples:
         * "How many mammal species..." → taxa=["Mammalia"]
         * "List cat families..." → taxa=["Felis"]
         * "Tell me about Canis familiaris" → taxa=["Canis familiaris"]
         * "... for humans and mice" → taxa=["Homo sapiens", "Mus musculus"]

    2. **assemblies**: If query is about genome assemblies
       - Provide assembly accession(s) (e.g., "GCF_000002305.6")
       - Examples:
         * "Details on assembly GCF_000002305.6" → assemblies=["GCF_000002305.6"]
         * "... for assemblies GCF_000002305.6 and GCA_000001405.28" →
           assemblies=["GCF_000002305.6", "GCA_000001405.28"]

    3. **samples**: If query is about DNA/RNA samples
       - Provide sample accession(s) (e.g., "SRR1234567")
       - Examples:
         * "Show sample SRR1234567" → samples=["SRR1234567"]
         * "... for samples SRR1234567 and SRR7654321" → samples=["SRR1234567", "SRR7654321"]

    4. **attributes**: Attribute names , values and modifiers to filter on or return
       - Example: "genome_size < 3G" → [{"name": "genome_size", "operator": "<", "value": "3000000000"}]
       - Combined modifiers: [{"name": "genome_size", "modifier": ["min", "direct"], "operator": "<", "value": "3G"}]
       - Summary modifiers: "min", "max", "median", "length"
       - Status modifiers (converted to exclusions): "missing", "direct", "ancestral", "descendant", "estimated"

    5. **fields**: Attribute names that should be returned as columns (if applicable)
       - Examples:
         * "Show genome_size and assembly_level" → [{"name": "genome_size"},
           {"name": "assembly_level"}]
         * "Show minimum genome_size and directly measured assembly_level" → [{"name": "genome_size", "modifier":
           ["min"]}, {"name": "assembly_level", "modifier": ["direct"]}]

    6. **rank**: Taxonomic rank if mentioned
       - Examples: "species", "family", "genus", "order", "class"
       - Only for queries that include a list of one or more taxa

    7. **intent**: What kind of result
       - "count": Just the count ("How many...")
       - "table": List of results ("Which...", "List...")

    8. **taxon_filter_type**: Infer the type of taxon filter to apply (if taxa provided)
       - Examples:
         * "families in Felis" → "children"
         * "matching Canis*", "for species A, species B and species C" → "matching"
         * "lineage of Mammalia", "parent taxa" → "lineage"

    9. **user_query**: Copy the original question for context. DO NOT modify this!

    For table results, you can also specify:
    10. **sort_by**: Optional field to sort results by (e.g., "genome_size")
    11. **sort_order**: Optional sort order - "asc" or "desc"
    12. **size**: Optional result size limit (default 10 for tables, None for counts)
                  Maximum size is 1000, but larger sizes may be slow.
    13. **page**: Optional page number for pagination (default 1)
"""

# Built-in LLM instruction prompt (default)
LLM_PROMPT_DEFAULT = """Follow these instructions exactly. Produce only a single JSON object as the
output (no prose). Do NOT modify the original `user_query`.

Output schema (exact keys):
- `user_query`: string (original query, unchanged)
- `taxa`: list of strings or []
- `assemblies`: list of strings or []
- `samples`: list of strings or []
- `rank`: string or null
- `attributes`: list of objects {"name","operator","value"(or null),"modifier"(optional list)}
    - `operator`: one of: `=`, `!=`, `<`, `<=`, `>`, `>=`, `exists`
    - `modifier`: allowed modifiers are the union of:
        - summary: `min`, `max`, `median`, `length`
        - status: `missing`, `direct`, `ancestral`, `descendant`, `estimated`
- `fields`: list of objects {"name", "modifier"(optional list)}
- `intent`: one of: `count`, `table`, `histogram`, `record`
- `taxon_filter_type`: one of: `children`, `matching`, `lineage` or null
- `search_index`: one of: `taxon`, `assembly`, `sample` or null
- `sort_by`: string or null
- `sort_order`: `asc`, `desc` or null
- `size`: integer or null
- `page`: integer (default 1)
- `parse_warnings`: list of short strings (optional)

Rules (strict):
- Use only the allowed values for `operator`, `modifier`, `intent`, `taxon_filter_type`,
    `search_index`, and `sort_order`.
- Do not invent IDs, taxa, attribute names, or numeric values. If ambiguous, return empty
    lists or `null` and add a concise `parse_warnings` entry explaining the ambiguity.
- Map common names when unambiguous: `mammal` → `Mammalia`, `cat` → `Felis`, `dog` →
    `Canis`. If ambiguous, leave `taxa` empty and add a `parse_warnings` entry.
- Recognize assembly accessions (prefixes `GCF_`, `GCA_`) and sample accessions (prefixes
    `SRR`, `ERR`, `SRX`, `SRS`, etc.) as literal tokens; do not invent or normalize
    accessions.
- Convert human-readable sizes when straightforward (examples: `3G` → 3000000000,
    `1.5M` → 1500000). If you convert, put the numeric value (integer) into `value` and add
    a `parse_warnings` note exactly like: `converted '3G' -> 3000000000`.
- For existence checks use `operator: "exists"` and set `value` to `null`.
- Combine OR by placing multiple values in `value` as a list; combine AND by creating
    separate attribute objects.
- Set `intent` from phrasing heuristics: phrases starting with or containing `How many`
    → `count`; `List`, `Which`, `Show` → `table`; `Histogram of` → `histogram`; `Record for`
    or a lone accession lookup → `record`.
- Infer `search_index`: prefer `taxon` if `taxa` present; else `assembly` if `assemblies`
    present; else `sample` if `samples` present. If `search_index` is inferred from wording
    without explicit IDs, add a `parse_warnings` entry explaining the inference.
- Do not hallucinate facts or create IDs. When uncertain, prefer empty values and a
    clear `parse_warnings` message.

Output requirements:
- Return exactly one valid JSON object and nothing else.
- Use `null` (not the string "null") for missing scalar values.
- Use empty lists `[]` for missing list values.
- Keep `page` as an integer (default to `1` if absent).

Examples (input -> required JSON):

1) Input: `How many mammal species have genome_size < 3G?`
Output (required):
```json
{
    "user_query": "How many mammal species have genome_size < 3G?",
    "taxa": ["Mammalia"],
    "assemblies": [],
    "samples": [],
    "rank": "species",
    "attributes": [
        {"name": "genome_size", "operator": "<", "value": 3000000000}
    ],
    "fields": [],
    "intent": "count",
    "taxon_filter_type": "children",
    "search_index": "taxon",
    "sort_by": null,
    "sort_order": null,
    "size": null,
    "page": 1,
    "parse_warnings": ["converted '3G' -> 3000000000"]
}
```

2) Input: `Show assemblies GCF_000002305.6 and GCA_000001405.28; include genome_size and
assembly_level; sort by genome_size desc; size 5`
Output (required):
```json
{
    "user_query": "Show assemblies GCF_000002305.6 and GCA_000001405.28; include genome_size
and assembly_level; sort by genome_size desc; size 5",
    "taxa": [],
    "assemblies": ["GCF_000002305.6", "GCA_000001405.28"],
    "samples": [],
    "rank": null,
    "attributes": [],
    "fields": [{"name": "genome_size"}, {"name": "assembly_level"}],
    "intent": "table",
    "taxon_filter_type": null,
    "search_index": "assembly",
    "sort_by": "genome_size",
    "sort_order": "desc",
    "size": 5,
    "page": 1
}
```

3) Input: `Show SRR1234567`
Output (required):
```json
{
    "user_query": "Show SRR1234567",
    "taxa": [],
    "assemblies": [],
    "samples": ["SRR1234567"],
    "rank": null,
    "attributes": [],
    "fields": [],
    "intent": "record",
    "taxon_filter_type": null,
    "search_index": "sample",
    "sort_by": null,
    "sort_order": null,
    "size": null,
    "page": 1
}
```

If a choice is uncertain, prefer leaving fields empty and provide a clear `parse_warnings`
entry.
"""

prompts = {
    "original": LLM_PROMPT_ORIGINAL,
    "default": LLM_PROMPT_DEFAULT,
}
