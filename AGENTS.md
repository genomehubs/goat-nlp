# Agent instructions for goat-nlp

## What this project is

A [FastMCP](https://gofastmcp.com) server that exposes genomic metadata search
as structured tools for LLMs. Tools query [GoaT (Genomes on a Tree)](https://goat.genomehubs.org)
through a pipeline of validation, artifact production, and query execution.
The server is designed to be redeployed against other GenomeHubs instances by
updating `src/mcp-server/config_site.py`.

## Before making any change

Read `src/mcp-server/tools/__init__.py` to understand which tool modules are
registered. Read the relevant tool file before editing it. Read
`src/mcp-server/config_example.py` to understand available config constants.

## Hard rules — do not violate these

- **No new HTTP calls.** All HTTP goes through `make_api_request()` in
  `src/mcp-server/tools/helpers/api.py`. A planned SDK migration will replace
  all direct API interactions; do not add new ones.
- **No new URL construction.** All URL building goes through
  `src/mcp-server/tools/helpers/query.py`. Do not construct URLs inline.
- **No hardcoded site values.** Use `DATASTORE_NAME`, `API_BASE`, `WEB_URL`,
  etc. from `src/mcp-server/config.py`. Never write `"GoaT"` or
  `"goat.genomehubs.org"` in tool code.
- **No new tool registration patterns.** Each tool module exposes
  `register_tools(mcp)` and is called from `tools/__init__.py`. Do not use
  `@mcp.tool()` decorators inline.
- **`log_tool_usage()` on every path.** Every public tool must call
  `log_tool_usage()` from `logging_config.py` on both success and failure paths,
  with `tool_name`, `params`, `duration_ms`, and `success`.

## Return types

- Tools that help the LLM choose parameters (`get_attribute_selection_context`,
  `get_attribute_info`, `get_attribute_guide`) return `str` (markdown).
- Pipeline tools (`process_identifiers`, `process_attributes`, `process_axis`,
  `submit_query`, `get_report`) return `dict` with a structured envelope
  including an `artifact_id` token for chaining.

## Prompt constants

LLM instructions are `TOOL_NAME_PROMPT` string constants in the same file as
the tool function. Rules for editing them:

- Do not add a failing query as a new example. Fix the instruction instead.
- One example per concept. Remove examples that duplicate a rule shown
  elsewhere in the same prompt.
- Attribute and rank names (`genome_size`, `phylum`) are acceptable domain
  terms. Specific taxon names, accession numbers, and project codes should be
  replaced with placeholders.
- Write positive instructions. Avoid `DO NOT` bullets where the positive
  equivalent is clear.
- Do not add sub-bullets or caveats to existing bullets. Rewrite the bullet.
- A prompt must not be longer after a fix than before unless a new concept is
  being added. Check line counts.

## Testing

There is no automated test runner. After any change:

```bash
python src/mcp-server/tests/smoke_histogram.py
python src/mcp-server/tests/smoke_submit_query_and_advanced_search.py
python src/mcp-server/tests/test_histogram_assert.py
```

Also verify the README examples manually against a running server — these are
the regression baseline.

## Known bugs — do not duplicate the root causes

- `get_report` is registered twice in `tools/report.py` `register_tools()`.
- `get_valid_ranks` is registered twice in `tools/utilities.py` `register_tools()`.
- `attribute_guide.register_tools` is never called from `tools/__init__.py`,
  so `get_attribute_guide` is unreachable as an MCP tool.
