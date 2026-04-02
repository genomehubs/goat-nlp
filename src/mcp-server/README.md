GenomeHubs MCP Server — Tools & Resources (Quick Reference)

Short guide to the tools and resources the `mcp-server` exposes for querying a GenomeHubs site.
Designed for users familiar with GenomeHubs but new to the MCP approach.

Individual instances should be site-scoped by updating the configuration as described in [CUSTOMISATION.md](CUSTOMISATION.md). The configuration defaults to GoaT/Genomes on a Tree, e.g. `SITE_NAME=goat`, etc.

**Tools**

- **Attributes:** `get_attribute_info`, `get_attribute_selection_context` — Inspect attribute metadata and help choose valid attribute names, modifiers and operators.
- **Process attributes:** `process_attributes` — Validate and canonicalise attribute filters, fields, names and ranks; returns an artifact token for downstream steps.
- **Process identifiers:** `process_identifiers` — Extract and validate taxa, assemblies, samples, rank and `taxon_filter_type`; returns an artifact token.
- **Query runner:** `submit_query` — Combine identifier and attribute artifacts into a query URL and execute the search; supports intents: `count`, `table`, `histogram`, `record`.
- **Utilities:** `choose_search_index`, `check_taxon_exists`, `get_valid_ranks` — Helpers for index selection, taxon validation, and fetching valid ranks.

**Resources**

- **`resource://{SITE_NAME}/description`** → `get_datastore_description` — Short human-readable description for prompts or UIs.

How they fit together (typical flow):

- Step 1: `process_identifiers` → produce identifiers artifact token.
- Step 2: `process_attributes` → produce attributes artifact token.
- Step 3: `submit_query` (pass both artifact tokens) → builds the query URL and returns results.

Notes & quick tips:

- Artifact tokens: `process_identifiers` and `process_attributes` return short-lived artifact IDs stored in the server; pass them unchanged into `submit_query`.
- Use `check_taxon_exists` to validate or translate common names to scientific names before querying.
- A debug HTTP route exists in the server for introspection of registered tools: `/debug/tools` (see [src/mcp-server/server.py](src/mcp-server/server.py)).

Want this added to the top-level README or turned into a one-page quickstart? Let me know.
