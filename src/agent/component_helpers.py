import json
import urllib
from datetime import datetime
from typing import Any, Dict

import requests
from llama_index.core import Settings
from llama_index.core.output_parsers.utils import extract_json_str

from prompt import (
    ATTRIBUTE_PROMPT,
    ENTITY_PROMPT,
    INDEX_PROMPT,
    INTENT_PROMPT,
    RANK_PROMPT,
    TIME_PROMPT,
)


def identify_index(input: str, state: Dict[str, Any]):
    index_response = Settings.llm.complete(INDEX_PROMPT.format(query=input)).text
    state["index"] = json.loads(extract_json_str(index_response))

    if "classification" not in state["index"] or "explanation" not in state["index"]:
        raise ValueError("Invalid response from model at index identification stage.")


def identify_entity(input: str, state: Dict[str, Any]):
    entity_response = Settings.llm.complete(ENTITY_PROMPT.format(query=input)).text
    state["entity"] = json.loads(extract_json_str(entity_response))

    if "entities" not in state["entity"] or "explanation" not in state["entity"]:
        raise ValueError("Invalid response from model at entity identification stage.")


def identify_rank(input: str, state: Dict[str, Any]):
    rank_response = Settings.llm.complete(RANK_PROMPT.format(query=input)).text
    state["rank"] = json.loads(extract_json_str(rank_response))

    if "rank" not in state["rank"] or "explanation" not in state["rank"]:
        raise ValueError("Invalid response from model at rank identification stage.")


def identify_time_frame(input: str, state: Dict[str, Any]):
    time_response = Settings.llm.complete(
        TIME_PROMPT.format(
            query=input, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    ).text
    state["timeframe"] = json.loads(extract_json_str(time_response))

    if (
        "from_date" not in state["timeframe"]
        or "to_date" not in state["timeframe"]
        or "explanation" not in state["timeframe"]
    ):
        raise ValueError(
            "Invalid response from model at timeframe identification stage."
        )


def identify_intent(input: str, state: Dict[str, Any]):
    intent_response = Settings.llm.complete(INTENT_PROMPT.format(query=input)).text
    state["intent"] = json.loads(extract_json_str(intent_response))

    if "intent" not in state["intent"] or "explanation" not in state["intent"]:
        raise ValueError("Invalid response from model at intent identification stage.")


def identify_attributes(input: str, state: Dict[str, Any]):
    response = requests.get(
        "https://goat.genomehubs.org/api/v2/resultFields"
        + f'?result={state["index"]["classification"]}'
        + "&taxonomy=ncbi"
    )
    response_parsed = response.json()
    cleaned_attributes = []

    for name, attribute in response_parsed["fields"].items():
        cleaned_attributes.append(
            {
                "name": name,
                "description": (
                    attribute["description"] if "description" in attribute else None
                ),
                "constraint": (
                    attribute["constraint"] if "constraint" in attribute else None
                ),
                "value_metadata": (
                    attribute["value_metadata"]
                    if "value_metadata" in attribute
                    else None
                ),
            }
        )

    attribute_response = Settings.llm.complete(
        ATTRIBUTE_PROMPT.format(
            attribute_metadata=json.dumps(cleaned_attributes, indent=4),
            query=input,
        )
    ).text
    state["attributes"] = json.loads(extract_json_str(attribute_response))

    if (
        "attributes" not in state["attributes"]
        or "explanation" not in state["attributes"]
    ):
        raise ValueError(
            "Invalid response from model at attribute identification stage."
        )


def construct_query(input: str, state: Dict[str, Any]):
    entities = ""
    for entity in state["entity"]["entities"]:
        entities += f"{entity['singular_form']},"
        entities += f"{entity['plural_form']},"
        entities += f"{entity['scientific_name']},"
        entities += f"* {entity['singular_form']},"
        entities += f"* {entity['plural_form']},"

    entities.removesuffix(",")

    query = ""

    if entities != "":
        query += f"tax_tree({entities}) AND "

    if state["rank"]["rank"] != "":
        query += f"tax_rank({state['rank']['rank']}) AND "

    if state["timeframe"]["from_date"] != "" or state["timeframe"]["to_date"] != "":
        state["index"]["classification"] = "assembly"
        if state["timeframe"]["from_date"] != "":
            query += f"last_updated>={state['timeframe']['from_date']} AND "
        if state["timeframe"]["to_date"] != "":
            query += f"last_updated<={state['timeframe']['to_date']} AND "

    if state["attributes"]["attributes"] != []:
        for attribute in state["attributes"]["attributes"]:
            condition = attribute["condition"]
            if condition == "in":
                query += (
                    f'{attribute["attribute"]}({",".join(attribute["value"])}) AND '
                )
            else:
                query += (
                    f'{attribute["attribute"]}'
                    + f'{attribute["condition"]}'
                    + f'{attribute["value"]} AND '
                )

    query.removesuffix(" AND ")

    state["query"] = query


def construct_url(input: str, state: Dict[str, Any]):
    base_url = "https://goat.genomehubs.org/"
    endpoint = state["intent"]["intent"] + "?"
    suffix = (
        f'&result={state["index"]["classification"]}'
        + "&summaryValues=count&taxonomy=ncbi&offset=0"
        + "&fields=assembly_level%2Cassembly_span%2Cgenome_size%2C"
        + "chromosome_number%2Chaploid_number&names=common_name&ranks="
        + "&includeEstimates=false&size=100"
    )

    state["final_url"] = (
        base_url + endpoint + "query=" + urllib.parse.quote(state["query"]) + suffix
    )
