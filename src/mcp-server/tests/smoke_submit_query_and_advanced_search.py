"""Zero-dependency smoke tests for submit_query and advanced_search.

Run with:
    python mcp-server/tests/smoke_submit_query_and_advanced_search.py
"""

import asyncio
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


search_mod = importlib.import_module("mcp-server.tools.search")
query_mod = importlib.import_module("mcp-server.tools.query_parser")
errors_mod = importlib.import_module("mcp-server.tools.helpers.errors")


class Patcher:
    def __init__(self):
        self._patches = []

    def set(self, module, name, value):
        original = getattr(module, name)
        self._patches.append((module, name, original))
        setattr(module, name, value)

    def restore(self):
        while self._patches:
            module, name, original = self._patches.pop()
            setattr(module, name, original)


async def test_advanced_search_core_data():
    patch = Patcher()
    try:
        async def fake_fetch_valid_types(_search_index):
            return {}

        def fake_validate_attributes(values, *_args, **_kwargs):
            return values

        def fake_validate_attribute_name(value, *_args, **_kwargs):
            return value

        async def fake_build_search_params(**_kwargs):
            return {"query": "tax_tree(Mollusca)"}

        def fake_params_dict_to_url(_base, _params):
            return "https://api.example/count"

        async def fake_make_api_request(_url):
            return {"count": 42}

        def fake_build_user_facing_url(_url):
            return "https://example/search?query=tax_tree(Mollusca)"

        patch.set(search_mod, "fetch_valid_types", fake_fetch_valid_types)
        patch.set(search_mod, "validate_attributes", fake_validate_attributes)
        patch.set(search_mod, "validate_attribute_name", fake_validate_attribute_name)
        patch.set(search_mod, "build_search_params", fake_build_search_params)
        patch.set(search_mod, "params_dict_to_url", fake_params_dict_to_url)
        patch.set(search_mod, "make_api_request", fake_make_api_request)
        patch.set(search_mod, "build_user_facing_url", fake_build_user_facing_url)

        result = await search_mod.advanced_search(
            search_index="taxon",
            taxa=["Mollusca"],
            rank="species",
            user_query="How many mollusca species are there?",
            show_table=False,
        )

        assert result["count"] == 42
        assert result["search_index"] == "taxon"
        assert "markdown" not in result
        assert "csv" not in result
        print("✓ test_advanced_search_core_data")
    finally:
        patch.restore()


async def test_advanced_search_handled_error():
    patch = Patcher()
    try:
        async def fake_fetch_valid_types(_search_index):
            return {}

        async def fake_build_search_params(**_kwargs):
            return {"query": "x"}

        def fake_params_dict_to_url(_base, _params):
            return "https://api.example/search"

        async def fake_make_api_request(_url):
            return {"status": {"hits": 0}}

        patch.set(search_mod, "fetch_valid_types", fake_fetch_valid_types)
        patch.set(search_mod, "build_search_params", fake_build_search_params)
        patch.set(search_mod, "params_dict_to_url", fake_params_dict_to_url)
        patch.set(search_mod, "make_api_request", fake_make_api_request)

        try:
            await search_mod.advanced_search(
                search_index="taxon",
                user_query="show table",
                show_table=True,
            )
        except errors_mod.ToolExecutionError:
            print("✓ test_advanced_search_handled_error")
            return

        raise AssertionError("Expected ToolExecutionError was not raised")
    finally:
        patch.restore()


async def test_submit_query_formatting_and_handled_error():
    patch = Patcher()
    try:
        identifiers = {
            "taxa": ["Mollusca"],
            "assemblies": [],
            "samples": [],
            "taxon_filter_type": "children",
            "rank": "species",
            "user_query": "give me mollusca chromosome level genomes",
            "search_index": "taxon",
        }
        attributes = {
            "attributes": [{"name": "assembly_level", "operator": "=", "value": "chromosome"}],
            "fields": [{"name": "genome_size"}, {"name": "scientific_name"}],
            "names": [],
            "ranks": [],
            "search_index": "assembly",
        }

        def fake_retrieve(artifact_id):
            if artifact_id == "id-artifact":
                return identifiers
            if artifact_id == "attr-artifact":
                return attributes
            return None

        def fake_resolve_index(_search_index, _identifiers_output, _attributes_output):
            return "assembly"

        async def fake_advanced_search(**_kwargs):
            return {
                "count": 1,
                "description": "1 assembly",
                "url": "https://example/search?x",
                "search_index": "assembly",
                "results": [
                    {
                        "result": {
                            "scientific_name": "Octopus vulgaris",
                            "fields": {"genome_size": {"value": 1000}},
                        }
                    }
                ],
                "api_response": {"results": []},
            }

        patch.set(query_mod, "retrieve", fake_retrieve)
        patch.set(query_mod, "resolve_index", fake_resolve_index)

        search_module = importlib.import_module("mcp-server.tools.search")
        patch.set(search_module, "advanced_search", fake_advanced_search)

        patch.set(
            query_mod,
            "process_result_table",
            lambda *_args, **_kwargs: {
                "columns": ["scientific_name"],
                "rows": [
                    {
                        "scientific_name": {
                            "value": "Octopus vulgaris",
                            "raw_value": "Octopus vulgaris",
                            "flag": False,
                        }
                    }
                ],
                "flags": 0,
            },
        )
        patch.set(
            query_mod,
            "format_result_table",
            lambda **kwargs: "formatted-csv" if kwargs.get("format") == "csv" else "formatted-markdown",
        )
        patch.set(query_mod, "set_search_tips", lambda *_args, **_kwargs: "tips")

        result = await query_mod.submit_query(
            identifiers_artifact_id="id-artifact",
            attributes_artifact_id="attr-artifact",
            intent="table",
            search_index="assembly",
            size=5,
            page=1,
        )

        assert result["result"]["csv"] == "formatted-csv"
        assert result["result"]["markdown"] == "formatted-markdown"

        async def fake_advanced_search_error(**_kwargs):
            raise errors_mod.ToolExecutionError("advanced_search", "handled failure")

        patch.set(search_module, "advanced_search", fake_advanced_search_error)

        handled = await query_mod.submit_query(
            identifiers_artifact_id="id-artifact",
            attributes_artifact_id="attr-artifact",
            intent="count",
            search_index="assembly",
        )

        assert handled["error_type"] == "handled"
        assert handled["error_tool"] == "advanced_search"
        print("✓ test_submit_query_formatting_and_handled_error")
    finally:
        patch.restore()


async def main():
    await test_advanced_search_core_data()
    await test_advanced_search_handled_error()
    await test_submit_query_formatting_and_handled_error()
    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
