import os

import pytest
from dotenv import load_dotenv
from llama_index.core import Settings, set_global_handler
from llama_index.core.query_pipeline import QueryPipeline as QP
from llama_index.llms.ollama import Ollama

from agent.component_helpers import (
    identify_entity,
    identify_index,
    identify_intent,
    identify_rank,
    identify_attributes,
    identify_time_frame,
    define_attribute_condition,
)
from agent.goat_query_component import GoatQueryComponent

load_dotenv()

Settings.llm = Ollama(
    model="llama3.1:8b-instruct-q4_0",
    base_url=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434"),
    request_timeout=36000.0,
)

set_global_handler("arize_phoenix")

QUERIES = [
    ("how many butterfly species do we know?", "taxon", "count", ["Lepidoptera"], "species", None, None, None, None),
    (
        "How many assemblies are available for the domestic dog?",
        "assembly",
        "count",
        ["Canis lupus familiaris"],
        None,
        None,
        None,
        None,
        None,
    ),
    (
        "Show me all the assemblies for gastropod molluscs",
        "assembly",
        "search",
        ["Gastropod"],
        None,
        None,
        None,
        None,
        None,
    ),
    (
        "What are the sequencing status values for bat families?",
        "taxon",
        "search",
        ["Chiroptera"],
        "family",
        None,
        None,
        None,
        None,
    ),
    (
        "Does Borneo magnolia have RNA-sequencing?",
        "taxon",
        "search",
        ["Magnolia"],
        "species",
        "sra_accession",
        "required",
        None,
        None,
    ),
    (
        "What are the contig N50 values for isopod and grass assemblies?",
        "assembly",
        "search",
        ["Isopoda", "Poaceae"],
        None,
        "contig_n50",
        "required",
        None,
        None,
    ),
    (
        "What is the sequencing status of bat families?",
        "taxon",
        "search",
        ["Chiroptera"],
        "family",
        "sequencing_status",
        "required",
        None,
        None,
    ),
    (
        "How many genome assemblies for fungi have been updated in August 2023?",
        "assembly",
        "count",
        ["Fungi"],
        None,
        None,
        None,
        "2023-08-01",
        "2023-08-31",
    ),
]


@pytest.mark.parametrize(
    "input_content, expected_index, _expected_intent, _expected_entities, _expected_rank, _expected_attribute, _expected_attribute_condition, _expected_time_from, _expected_time_to",
    QUERIES,
)
def test_index_module(
    input_content,
    expected_index,
    _expected_intent,
    _expected_entities,
    _expected_rank,
    _expected_attribute,
    _expected_attribute_condition,
    _expected_time_from,
    _expected_time_to,
):
    # Skip the test if no expected index is provided
    if expected_index is None:
        pytest.skip("No expected index for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the index module to the QueryPipeline
    qp.add_modules({"index": GoatQueryComponent(fn=identify_index)})

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": input_content, "state": {}})

    # Assert the expected index matches the result
    assert result["state"]["index"]["classification"] == expected_index


@pytest.mark.parametrize(
    "input_content, _expected_index, expected_intent, _expected_entities, _expected_rank, _expected_attribute, _expected_attribute_condition, _expected_time_from, _expected_time_to",
    QUERIES,
)
def test_intent_module(
    input_content,
    _expected_index,
    expected_intent,
    _expected_entities,
    _expected_rank,
    _expected_attribute,
    _expected_attribute_condition,
    _expected_time_from,
    _expected_time_to,
):
    # Skip the test if no expected intent is provided
    if expected_intent is None:
        pytest.skip("No expected intent for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the intent module to the QueryPipeline
    qp.add_modules({"intent": GoatQueryComponent(fn=identify_intent)})

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": input_content, "state": {}})

    # Assert the expected intent matches the result
    assert result["state"]["intent"]["intent"] == expected_intent


@pytest.mark.parametrize(
    "input_content, _expected_index, _expected_intent, expected_entities, _expected_rank, _expected_attribute, _expected_attribute_condition, _expected_time_from, _expected_time_to",
    QUERIES,
)
def test_entity_module(
    input_content,
    _expected_index,
    _expected_intent,
    expected_entities,
    _expected_rank,
    _expected_attribute,
    _expected_attribute_condition,
    _expected_time_from,
    _expected_time_to,
):
    # Skip the test if no expected entities are provided
    if expected_entities is None:
        pytest.skip("No expected entities for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the entity module to the QueryPipeline
    qp.add_modules({"entity": GoatQueryComponent(fn=identify_entity)})

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": input_content, "state": {}})

    # Assert the expected entity matches the result
    entities = result["state"]["entity"]["entities"]
    assert len(entities) == len(expected_entities)
    for entity in entities:
        assert (
            (entity["scientific_name"].lower() in [x.lower() for x in expected_entities])
            or (entity["singular_form"].lower() in [x.lower() for x in expected_entities])
            or (entity["plural_form"].lower() in [x.lower() for x in expected_entities])
        )


@pytest.mark.parametrize(
    "input_content, expected_index, expected_intent, expected_entities, expected_rank, _expected_attribute, _expected_attribute_condition, _expected_time_from, _expected_time_to",
    QUERIES,
)
def test_rank_module(
    input_content,
    expected_index,
    expected_intent,
    expected_entities,
    expected_rank,
    _expected_attribute,
    _expected_attribute_condition,
    _expected_time_from,
    _expected_time_to,
):
    # Skip the test if no expected rank is provided
    if expected_rank is None:
        pytest.skip("No expected rank for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the rank module to the QueryPipeline
    qp.add_modules({"rank": GoatQueryComponent(fn=identify_rank)})

    # Execute the QueryPipeline for the input data
    result = qp.run(
        input={
            "input": input_content,
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

    # Assert the expected rank matches the result
    assert result["state"]["rank"]["rank"] == expected_rank


@pytest.mark.parametrize(
    "input_content, expected_index, _expected_intent, _expected_entities, _expected_rank, expected_attribute, _expected_attribute_condition, _expected_time_from, _expected_time_to",
    QUERIES,
)
def test_attribute_module(
    input_content,
    expected_index,
    _expected_intent,
    _expected_entities,
    _expected_rank,
    expected_attribute,
    _expected_attribute_condition,
    _expected_time_from,
    _expected_time_to,
):
    # Skip the test if no expected attribute is provided
    if expected_attribute is None:
        pytest.skip("No expected attribute for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the attribute module to the QueryPipeline
    qp.add_modules({"attribute": GoatQueryComponent(fn=identify_attributes)})  # Corrected function name

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": input_content, "state": {"index": {"classification": expected_index}}})

    # Assert the expected attribute matches the result
    assert expected_attribute in result["state"]["attribute_identification"]["attributes"]


@pytest.mark.parametrize(
    "input_content, _expected_index, _expected_intent, _expected_entities, _expected_rank, _expected_attribute, _expected_attribute_condition, expected_time_from, expected_time_to",
    QUERIES,
)
def test_time_module(
    input_content,
    _expected_index,
    _expected_intent,
    _expected_entities,
    _expected_rank,
    _expected_attribute,
    _expected_attribute_condition,
    expected_time_from,
    expected_time_to,
):
    # Skip the test if no expected time is provided
    if expected_time_from is None and expected_time_to is None:
        pytest.skip("No expected time for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the time module to the QueryPipeline
    qp.add_modules({"time": GoatQueryComponent(fn=identify_time_frame)})

    # Execute the QueryPipeline for the input data
    result = qp.run(input={"input": input_content, "state": {}})

    # Assert the expected time matches the result
    assert (
        result["state"]["timeframe"]["from_date"] == expected_time_from
        and result["state"]["timeframe"]["to_date"] == expected_time_to
    )


@pytest.mark.parametrize(
    "input_content, expected_index, _expected_intent, _expected_entities, _expected_rank, expected_attribute, expected_attribute_condition, _expected_time_from, _expected_time_to",
    QUERIES,
)
def test_define_attribute_condition(
    input_content,
    expected_index,
    _expected_intent,
    _expected_entities,
    _expected_rank,
    expected_attribute,
    expected_attribute_condition,
    _expected_time_from,
    _expected_time_to,
):
    # Skip the test if no expected attribute is provided
    if expected_attribute is None or expected_attribute_condition is None:
        pytest.skip("No expected attribute for this test case")

    # Create a QueryPipeline instance
    qp = QP(verbose=True)

    # Add the define_attribute_condition module to the QueryPipeline
    qp.add_modules({"define_attribute_condition": GoatQueryComponent(fn=define_attribute_condition)})

    # Execute the QueryPipeline for the input data
    result = qp.run(
        input={
            "input": input_content,
            "state": {
                "index": {"classification": expected_index},
                "attribute_identification": {"attributes": [expected_attribute]},
            },
        }
    )

    # Assert the expected attribute condition matches the result
    assert result["state"]["attributes"]["attributes"][0]["condition"] == expected_attribute_condition
