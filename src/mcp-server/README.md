GoaT MCP Server — Tools & Resources (Quick Reference)

Short guide to the tools and resources the `mcp-server` exposes for querying GoaT.
Designed for users familiar with GoaT but new to the MCP approach.

**Tools**

- **Attributes:** `get_metadata_for_attribute`, `get_attribute_selection_context` — Inspect GoaT attribute metadata and help choose valid attribute names, modifiers and operators.
- **Process attributes:** `process_attributes` — Validate and canonicalise attribute filters, fields, names and ranks; returns an artifact token for downstream steps.
- **Process identifiers:** `process_identifiers` — Extract and validate taxa, assemblies, samples, rank and `taxon_filter_type`; returns an artifact token.
- **Query runner:** `goat_query` — Combine identifier and attribute artifacts into a GoaT query URL and execute the search; supports intents: `count`, `table`, `histogram`, `record`.
- **Utilities:** `choose_search_index`, `check_taxon_exists`, `get_example_queries`, `get_valid_ranks` — Helpers for index selection, taxon validation, example queries, and fetching valid ranks.

**Resources**

- **`resource://goat/description`** → `get_goat_description` — Short human-readable GoaT description for prompts or UIs.
- **`resource://goat/example-queries`** → `get_example_queries_resource` — Curated example queries grouped by category to guide users and LLM prompts.

How they fit together (typical flow):

- Step 1: `process_identifiers` → produce identifiers artifact token.
- Step 2: `process_attributes` → produce attributes artifact token.
- Step 3: `goat_query` (pass both artifact tokens) → builds the GoaT URL and returns results.

Notes & quick tips:

- Artifact tokens: `process_identifiers` and `process_attributes` return short-lived artifact IDs stored in the server; pass them unchanged into `goat_query`.
- Use `check_taxon_exists` to validate or translate common names to scientific names before querying.
- A debug HTTP route exists in the server for introspection of registered tools: `/debug/tools` (see [src/mcp-server/goat.py](src/mcp-server/goat.py)).

Want this added to the top-level README or turned into a one-page quickstart? Let me know.
