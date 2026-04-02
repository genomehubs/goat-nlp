# GitHub Copilot instructions for goat-nlp

## Project structure

```
src/mcp-server/
  server.py                  # FastMCP server entry point
  config.py                  # Imports from config_site.py (not tracked) or config_example.py
  config_example.py          # Edit this to create config_site.py for local config
  prompts/
    system.py                # Multi-stage system prompt (get_multi_stage_prompt)
    query_parser.py          # Legacy and default single-stage prompts
  tools/
    __init__.py              # Registers all tool modules via register_tools(mcp)
    attributes.py            # get_attribute_info, get_attribute_selection_context → return str
    attribute_guide.py       # get_attribute_guide → returns str
    utilities.py             # choose_search_index, check_taxon_exists, get_valid_ranks
    process_identifiers.py   # process_identifiers → returns artifact dict
    process_attributes.py    # process_attributes → returns artifact dict
    process_axis.py          # process_axis → returns artifact dict
    query_parser.py          # submit_query → returns result dict
    report.py                # get_report → returns result dict
    helpers/
      api.py                 # make_api_request — ONLY place for HTTP calls
      fetch.py               # fetch_valid_types — attribute metadata cache
      query.py               # URL/query string construction
      urls.py                # URL update utilities
      constants.py           # FIELD_CACHE (module-level attribute cache)
      validation.py          # validate_attributes, validate_attribute_name
      errors.py              # ToolExecutionError and error message helpers
      formatting.py          # process_result_table, format_result_table
      search_index.py        # infer_index_from_query
      processor_common.py    # finalise_and_store (artifact store writes)
  tests/
    smoke_histogram.py
    smoke_submit_query_and_advanced_search.py
    test_histogram_assert.py
    test_local_model_integration_scaffold.py
```

## Return type convention

- **Helper tools** (`get_attribute_info`, `get_attribute_selection_context`,
  `get_attribute_guide`) return `str` (markdown). FastMCP serialises these as
  `TextContent` — the LLM reads them directly.
- **Pipeline tools** (`process_*`, `submit_query`, `get_report`) return `dict`
  with a structured envelope. FastMCP serialises these as `structured_content`
  alongside `TextContent`.

## Hard constraints

**No new API calls outside the helpers layer.**
All HTTP is done through `make_api_request()` in `tools/helpers/api.py`.
A planned SDK migration will replace all direct API interactions. Until it
lands, do not add new `make_api_request` calls, new endpoints, or new
response-parsing logic anywhere outside `helpers/api.py`, `helpers/fetch.py`,
and `tools/utilities.py`.

**No new URL construction.**
All query URL building goes through `tools/helpers/query.py`. Do not construct
API or web URLs inline in tool functions.

**Config constants only — no hardcoded site values.**
Use `DATASTORE_NAME`, `API_BASE`, `WEB_URL`, etc. from `config.py`. Never
write `"GoaT"`, `"goat.genomehubs.org"`, or similar strings in tool code.

**Tool registration via `register_tools`.**
Each tool module exposes `register_tools(mcp)`. Import and call it from
`tools/__init__.py`. Do not decorate tool functions with `@mcp.tool()` inline.

**Every public tool must call `log_tool_usage()`.**
Both success and failure paths. Required fields: `tool_name`, `params`,
`duration_ms`, `success`. Failure paths also pass `error=` and optionally
`exc=`.

## Prompt editing rules

LLM instructions live as `TOOL_NAME_PROMPT` string constants in the same file
as the tool, assigned to the function's `__doc__`. When editing them:

1. **Fix the instruction, not the example.** If a query fails, find the missing
   or ambiguous rule and fix it. Do not add the failing query as a new example.

2. **One example per concept.** A single case is enough to demonstrate a
   pattern. Remove examples that duplicate a rule shown elsewhere in the prompt.

3. **Domain terms are fine; specific instances are not.** Attribute names
   (`genome_size`, `assembly_level`) and rank names (`phylum`, `species`) are
   unavoidable. Specific taxon names, accession numbers, and project codes
   should be replaced with placeholders unless they are the clearest way to
   show a structural point.

4. **Positive over prohibitive.** Write "pass values as a list" rather than
   "do not pass as a string". Prohibitions accumulate; positive rules compose.

5. **Rewrite bullets, don't append to them.** If a bullet is unclear, rewrite
   it. Do not add a sub-bullet or parenthetical caveat.

6. **Prompts must not grow without reason.** Check line count before and after.
   A fix should not increase length unless it adds support for a new concept.

## Testing

No automated runner. After any change:

1. Run the smoke tests:
   ```
   python src/mcp-server/tests/smoke_histogram.py
   python src/mcp-server/tests/smoke_submit_query_and_advanced_search.py
   python src/mcp-server/tests/test_histogram_assert.py
   ```
2. Verify README examples manually against a running server. These are the
   regression baseline.

## Known bugs (do not duplicate the root causes)

- `get_report` registered twice in `tools/report.py` `register_tools()`.
- `get_valid_ranks` registered twice in `tools/utilities.py` `register_tools()`.
- `attribute_guide.register_tools` not called from `tools/__init__.py` —
  `get_attribute_guide` is currently unreachable as an MCP tool.
