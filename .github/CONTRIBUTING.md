# Contributing to GoaT-NLP

## Architecture overview

The project exposes a [FastMCP](https://gofastmcp.com) server that lets LLMs query
[GoaT (Genomes on a Tree)](https://goat.genomehubs.org) through a structured tool pipeline:

```
choose_search_index / check_taxon_exists / get_attribute_selection_context
        ↓
process_identifiers  +  process_attributes  (parallel)
        ↓
submit_query  or  get_report
```

Helper tools (`get_attribute_selection_context`, `get_attribute_info`,
`get_attribute_guide`) return plain markdown strings — the LLM reads them
as text. Pipeline tools (`process_*`, `submit_query`, `get_report`) return
structured dicts for machine-readable chaining via artifact tokens.

Site-specific configuration (API base URL, site name, branding) lives in
`src/mcp-server/config_site.py` which is not tracked by git. Copy
`config_example.py` as a starting point:

```bash
cp src/mcp-server/config_example.py src/mcp-server/config_site.py
```

To run the server:

```bash
pip install -r requirements.txt
python -m src.mcp-server.server
```

---

## Where contributor effort has most impact right now

**Prompt refinement is the highest-value area.** The LLM instructions embedded
in each tool docstring (`PROCESS_ATTRIBUTES_PROMPT`, `PROCESS_IDENTIFIERS_PROMPT`,
etc.) directly control query quality. A well-targeted prompt edit can fix a
class of failures for all users and all LLMs.

### Known prompt issues to address

- **`LLM_PROMPT_DEFAULT`** (`prompts/query_parser.py`): the three JSON examples
  at the end use specific taxa (`Mammalia`) and accessions (`GCF_000002305.6`,
  `SRR1234567`). The first two examples could be made more abstract; the third
  is acceptable as a minimal illustration.

- **`PROCESS_IDENTIFIERS_PROMPT`** (`tools/process_identifiers.py`): repeats
  common-name mappings (`mammal→Mammalia`, `cat→Felis`) already in the system
  prompt. Remove the duplication. The end example shares the same
  `genome_size < 3G` / `Felis` scenario as `PROCESS_ATTRIBUTES_PROMPT` — one
  of them should use a different illustrative query.

- **`PROCESS_ATTRIBUTES_PROMPT`** (`tools/process_attributes.py`): the name
  filter examples in section 3 use `'Canis'` as a value — replace with a
  generic placeholder. Convert any remaining `DO NOT` / `MUST NOT` bullets to
  positive instructions where the intent can be expressed that way.

- **`GET_REPORT_PROMPT`** (`tools/report.py`): `api_url` in the return envelope
  description is hardcoded as "The GoaT API URL" — use `DATASTORE_NAME` for
  generality. The `report` backward-compatibility key should carry a
  deprecation note.

- **`SUBMIT_QUERY_PROMPT`** (`tools/query_parser.py`): `response_format="full"`
  is marked `(future)` inside the prompt — move this to a code comment or
  remove it from the prompt entirely. Replace the `⚠️` emoji with plain text.

- **`system.py` → `get_multi_stage_prompt()`**: add a signal for when to use
  `get_report` vs `submit_query` (currently the distinction is only implied).
  Deduplicate the `choose_search_index` guidance which appears in both the
  numbered steps and the NOTES section.

- **`PROCESS_AXIS_PROMPT`** (`tools/process_axis.py`): references
  `process_axis_complex()` as an alternative in two places; this tool does not
  exist yet. Replace with a note that complex axes are not currently supported,
  or remove the references until the tool is implemented.

---

## Prompt editing rules

These rules exist to keep prompts effective and prevent gradual bloat:

1. **Fix the instruction, not the example.** If a query fails, identify the
   missing or ambiguous rule and restate it clearly. Do not add the failing
   query as a new example to the prompt.

2. **One example per concept.** A single illustrative case is enough to
   demonstrate a pattern. Remove examples that duplicate a rule already shown
   elsewhere in the same prompt.

3. **Real-world examples only when unavoidable.** Attribute and rank names
   (`genome_size`, `phylum`) are domain terms that must appear. Specific taxon
   names, accession numbers, and project names should be replaced with
   placeholders (`<taxon>`, `<accession>`) unless they are genuinely the
   clearest way to illustrate a structural point.

4. **Prefer positive instructions.** Write "pass values as a list" rather than
   "do not pass as a string". Prohibitions accumulate; instructions get
   overwritten.

5. **Rewrite, don't append.** If an existing bullet is unclear, rewrite it.
   Do not add a clarifying sub-bullet or parenthetical caveat — the prompt will
   grow with each iteration.

6. **Measure prompt length.** Note the line count before and after your edit.
   A prompt should not be longer after a fix than before, except when adding
   support for a genuinely new concept.

---

## Testing

There is no automated test runner. Regression testing is manual:

1. Run the smoke tests:

   ```bash
   python src/mcp-server/tests/smoke_histogram.py
   python src/mcp-server/tests/smoke_submit_query_and_advanced_search.py
   python src/mcp-server/tests/test_histogram_assert.py
   ```

2. Verify the mcp-server/README examples manually against a running server. These are the
   canonical regression baseline. Any prompt change that causes a previously
   correct README example to produce a wrong result is a regression.

3. For local model testing (requires `mcphost` and a running Ollama instance, this is incomplete):
   ```bash
   export LOCAL_MODEL_CMD="~/go/bin/mcphost --quiet --provider-url http://localhost:11434 \
     --config src/mcp-server/tests/mcp-host.yml -m {model} -p {prompt}"
   export LOCAL_MODEL_NAME="ollama:llama3.1:8b"
   python3 src/mcp-server/tests/test_local_model_integration_scaffold.py
   ```

---

## Architecture constraints — read before adding code

**No new API interactions until the SDK is in place.**
A major refactor is planned to move all API calls and URL construction into a
dedicated SDK module. Until that is merged:

- Do not add new calls to `make_api_request()` outside `tools/helpers/api.py`,
  `tools/helpers/fetch.py`, or `tools/utilities.py`.
- Do not add new URL construction patterns. All URL building goes through
  `tools/helpers/query.py` (`build_query_string`, `build_user_facing_url`,
  `params_dict_to_url`).
- Do not add new endpoints or new result-field parsing logic.

**Configuration is site-scoped.**
All site-specific values (`API_BASE`, `WEB_URL`, `DATASTORE_NAME`, etc.) come
from `config_site.py` → `config_example.py`. Never hardcode GoaT-specific
values into tool code; use the config constants.

**Tool registration follows a fixed pattern.**
Each tool module defines a `register_tools(mcp)` function and is imported in
`tools/__init__.py`. Do not register tools inline in `server.py`.

**Caching uses the established TTL pattern.**
Attribute types and taxon ranks are cached with a 24-hour TTL using
module-level dicts/lists + timestamps (`FIELD_CACHE`, `RANK_CACHE`). Do not
introduce new cache implementations.

**Every public tool must call `log_tool_usage()`.**
Both success and failure paths must log via `log_tool_usage()` from
`logging_config.py`. The call must include `tool_name`, `params`,
`duration_ms`, and `success`.

---

## Known bugs (help welcome)

- `get_report` is registered twice in `tools/report.py` `register_tools()`.
- `get_valid_ranks` is registered twice in `tools/utilities.py` `register_tools()`.
- `attribute_guide.register_tools` is never called from `tools/__init__.py`,
  so `get_attribute_guide` is currently unreachable as an MCP tool.

---

## PR checklist

- [ ] Smoke tests pass
- [ ] README examples still produce correct output when tested manually
- [ ] No new `make_api_request` calls outside the helpers layer
- [ ] No hardcoded site-specific values (use config constants)
- [ ] Prompt changes do not increase line count without adding a new concept
- [ ] `log_tool_usage()` called on all paths in any new or modified tool
