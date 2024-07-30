import os

from dotenv import load_dotenv
import pytest
from llama_index.core import Settings, set_global_handler
from llama_index.core.query_pipeline import QueryPipeline as QP
from llama_index.llms.ollama import Ollama

from agent.component_helpers import (
    identify_entity,
    identify_index,
    identify_intent,
    identify_rank,
)
from agent.goat_query_component import GoatQueryComponent

load_dotenv()

Settings.llm = Ollama(
    model="llama3.1",
    base_url=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434"),
    request_timeout=36000.0,
)

set_global_handler("arize_phoenix")

QUERIES = [
    # (input_content, expected_index, expected_intent, expected_entities, expected_rank)
    (
        "how many butterfly species have a directly measured genome size value?",
        "taxon",
        "count",
        ["Lepidoptera"],
        "species",
    ),
    ("How many assemblies are available for the domestic dog?", "assembly", "count", ["Canis lupus familiaris"], ""),
    ("Show me all the assemblies for gastropod molluscs", "assembly", "search", ["Gastropoda"], ""),
    ("What are the sequencing status values for bat families?", "taxon", "search", ["Chiroptera"], "family"),
    (
        "What are the contig N50 values for isopod and grass assemblies?",
        "assembly",
        "search",
        ["Isopoda", "Poaceae"],
        "",
    ),
    (
        "What are the sequencing status and target list values for bat families?",
        "taxon",
        "search",
        ["Chiroptera"],
        "family",
    ),
    (
        "How does contig N50 vary with genome size for species in the phylum chordata?",
        "taxon",
        "scatter",
        ["Chordata"],
        "species",
    ),
    ("Give me a tree of molluscs with an assembly span over 2Gbp", "taxon", "tree", ["Mollusca"], ""),
    (
        "Show me the distribution of haploid chromosome numbers across all insect orders",
        "taxon",
        "histogram",
        ["Insecta"],
        "order",
    ),
    ("what are the locations of all samples under the DToL project?", "sample", "search", [], None),
    ("how does assembly span vary with genome size across all phyla?", "taxon", "scatter", [], "phylum"),
]


@pytest.mark.parametrize(
    "input_content, expected_index, _expected_intent, _expected_entities, _expected_rank", QUERIES
)
def test_index_module(input_content, expected_index, _expected_intent, _expected_entities, _expected_rank):
    # Skip the test if no expected intent is provided
    if expected_index is None:
        pytest.skip("No expected index for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the intent module to the QueryPipeline
    qp.add_modules({"intent": GoatQueryComponent(fn=identify_index)})

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": {"role": "user", "content": input_content}, "state": {}})

    # Assert the expected intent matches the result
    assert result["state"]["index"]["classification"] == expected_index


@pytest.mark.parametrize(
    "input_content, _expected_index, expected_intent, _expected_entities, _expected_rank", QUERIES
)
def test_intent_module(input_content, _expected_index, expected_intent, _expected_entities, _expected_rank):
    # Skip the test if no expected intent is provided
    if expected_intent is None:
        pytest.skip("No expected intent for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the intent module to the QueryPipeline
    qp.add_modules({"intent": GoatQueryComponent(fn=identify_intent)})

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": {"role": "user", "content": input_content}, "state": {}})

    # Assert the expected intent matches the result
    assert result["state"]["intent"]["intent"] == expected_intent


@pytest.mark.parametrize(
    "input_content, _expected_index, _expected_intent, expected_entities, _expected_rank", QUERIES
)
def test_entity_module(input_content, _expected_index, _expected_intent, expected_entities, _expected_rank):
    # Skip the test if no expected entities are provided
    if expected_entities is None:
        pytest.skip("No expected entities for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the entity module to the QueryPipeline
    qp.add_modules({"entity": GoatQueryComponent(fn=identify_entity)})

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": {"role": "user", "content": input_content}, "state": {}})

    # Assert the expected entity matches the result
    entities = result["state"]["entity"]["entities"]
    assert len(entities) == len(expected_entities)
    for entity in entities:
        assert entity["scientific_name"] in expected_entities


@pytest.mark.parametrize("input_content, expected_index, expected_intent, expected_entities, expected_rank", QUERIES)
def test_rank_module(input_content, expected_index, expected_intent, expected_entities, expected_rank):
    # Skip the test if no expected intent is provided
    if expected_rank is None:
        pytest.skip("No expected intent for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the intent module to the QueryPipeline
    qp.add_modules({"rank": GoatQueryComponent(fn=identify_rank)})

    # Execute the QueryPipeline for the input data
    result = qp.run(
        input={
            "input": {"role": "user", "content": input_content},
            "state": {
                "intent": {"intent": expected_intent},
                "index": {"classification": expected_index},
                "entity": {
                    "entities": [
                        {"scientific_name": expected_entity, "singular_form": "", "plural_form": ""}
                        for expected_entity in expected_entities
                    ]
                },
            },
        }
    )

    # Assert the expected intent matches the result
    assert result["state"]["rank"]["rank"] == expected_rank
