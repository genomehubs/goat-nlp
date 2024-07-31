import json
import logging
import os
import urllib
from datetime import datetime
from typing import Any, Dict

import cachetools.func
import requests
from llama_index.core import Settings
from llama_index.core.output_parsers.utils import extract_json_str

from prompt import (
    ATTRIBUTE_PROMPT,
    ENTITY_PROMPT,
    INDEX_PROMPT,
    INTENT_PROMPT,
    LINEAGE_PROMPT,
    RANK_PROMPT,
    RECORD_PROMPT,
    TIME_PROMPT,
)

logger = logging.getLogger("goat_nlp.component_helpers")


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
    cleaned_taxons = query_entity(state, query_operator="tax_tree", include_sub_species=False)
    rank_response = Settings.llm.complete(
        RANK_PROMPT.format(query=input, results=json.dumps(cleaned_taxons, indent=4))
    ).text
    state["rank"] = json.loads(extract_json_str(rank_response))

    if "rank" not in state["rank"] or "explanation" not in state["rank"]:
        raise ValueError("Invalid response from model at rank identification stage.")


def identify_time_frame(input: str, state: Dict[str, Any]):
    time_response = Settings.llm.complete(
        TIME_PROMPT.format(query=input, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ).text
    state["timeframe"] = json.loads(extract_json_str(time_response))

    if (
        "from_date" not in state["timeframe"]
        or "to_date" not in state["timeframe"]
        or "explanation" not in state["timeframe"]
    ):
        raise ValueError("Invalid response from model at timeframe identification stage.")


def identify_intent(input: str, state: Dict[str, Any]):
    intent_response = Settings.llm.complete(INTENT_PROMPT.format(query=input)).text
    state["intent"] = json.loads(extract_json_str(intent_response))

    if "intent" not in state["intent"] or "explanation" not in state["intent"]:
        raise ValueError("Invalid response from model at intent identification stage.")


@cachetools.func.ttl_cache(ttl=int(os.getenv("ATTRIBUTE_API_TTL", 2 * 24 * 60 * 60)))
def attribute_api_call(index: str):
    response = requests.get(f'{os.getenv("GOAT_BASE_URL")}/resultFields?result={index}&taxonomy=ncbi')

    logger.info(f"Made API call for {index} endpoint")

    response_parsed = response.json()
    return response_parsed if response_parsed["status"]["success"] else None


def identify_attributes(input: str, state: Dict[str, Any]):

    attributes = attribute_api_call(state["index"]["classification"])
    cleaned_attributes = [
        {
            "name": name,
            "description": (attribute["description"] if "description" in attribute else None),
            "constraint": (attribute["constraint"] if "constraint" in attribute else None),
            "value_metadata": (attribute["value_metadata"] if "value_metadata" in attribute else None),
        }
        for name, attribute in attributes["fields"].items()
    ]

    attribute_response = Settings.llm.complete(
        ATTRIBUTE_PROMPT.format(
            attribute_metadata=json.dumps(cleaned_attributes, indent=4),
            query=input,
        )
    ).text
    state["attributes"] = json.loads(extract_json_str(attribute_response))

    if "attributes" not in state["attributes"] or "explanation" not in state["attributes"]:
        raise ValueError("Invalid response from model at attribute identification stage.")


def construct_query(input: str, state: Dict[str, Any]):
    query = ""

    if state["rank"]["rank"] != "":
        if "taxon_id" in state["rank"] and state["rank"]["taxon_id"]:
            taxon_id_filter = f"tax_name({str(state['rank']['taxon_id'])})"
            query_url = f"{os.getenv('GOAT_BASE_URL')}/search?query={urllib.parse.quote(taxon_id_filter)}"
            query_url += f"&result={state['index']['classification']}"

            response = requests.get(query_url)
            response_parsed = response.json()

            if not response_parsed["status"]["success"]:
                raise ValueError("Error querying API to fetch taxon lineage details.")

            parent_taxon_id_response = Settings.llm.complete(
                LINEAGE_PROMPT.format(
                    query=input, lineage=json.dumps(response_parsed["results"][0]["result"]["lineage"], indent=4)
                )
            ).text
            try:
                parent_taxon_id = json.loads(extract_json_str(parent_taxon_id_response))["taxon_id"]
                state["lineage"] = parent_taxon_id_response
            except Exception as e:
                raise ValueError("Error fetching parent taxon id from lineage details from model.") from e
            query += f"tax_tree({parent_taxon_id}) AND "
        query += f"tax_rank({state['rank']['rank']}) AND "

    if state["timeframe"]["from_date"] != "" or state["timeframe"]["to_date"] != "":
        state["index"]["classification"] = "assembly"
    if state["timeframe"]["from_date"] != "":
        query += f"last_updated>={state['timeframe']['from_date']} AND "
    if state["timeframe"]["to_date"] != "":
        query += f"last_updated<={state['timeframe']['to_date']} AND "

    if state["attributes"]["attributes"] != []:
        for attribute in state["attributes"]["attributes"]:
            if attribute["condition"] is None or attribute["value"] is None:
                continue
            condition = attribute["condition"]
            if condition == "in":
                query += f'{attribute["attribute"]}({",".join(attribute["value"])}) AND '
            else:
                query += f'{attribute["attribute"]}' + f'{attribute["condition"]}' + f'{attribute["value"]} AND '

    query = query.removesuffix(" AND ")

    state["query"] = query


def construct_url(input: str, state: Dict[str, Any]):
    base_url = "https://goat.genomehubs.org/"
    endpoint = state["intent"]["intent"] + "?"
    suffix = f'&result={state["index"]["classification"]}&summaryValues=count&taxonomy=ncbi&offset=0'
    suffix += "&fields=assembly_level%2Cassembly_span%2Cgenome_size%2Cchromosome_number%2C"
    suffix += "haploid_number&names=common_name&ranks=&includeEstimates=false&size=100"

    state["final_url"] = base_url + endpoint + "query=" + urllib.parse.quote(state["query"]) + suffix


def identify_record(input: str, state: Dict[str, Any]):
    cleaned_taxons = query_entity(state)

    for taxon in cleaned_taxons:
        taxon.pop("lineage", None)

    taxon_response = Settings.llm.complete(
        RECORD_PROMPT.format(query=input, results=json.dumps(cleaned_taxons, indent=4))
    ).text
    state["record"] = json.loads(extract_json_str(taxon_response))

    if "taxon_id" not in state["record"] or "explanation" not in state["record"]:
        raise ValueError("Invalid response from model at record identification stage.")

    state["final_url"] = (
        "https://goat.genomehubs.org/record?recordId="
        + str(state["record"]["taxon_id"])
        + f"&result={state['index']['classification']}"
    )


def query_entity(state: Dict[str, Any], query_operator="tax_name", include_sub_species=True) -> list:
    if "entities" not in state["entity"] or state["entity"]["entities"] == []:
        return []
    entities = ""
    for entity in state["entity"]["entities"]:
        entities += f"{entity['singular_form']},"
        entities += f"{entity['plural_form']},"
        entities += f"{entity['scientific_name']},"
        if include_sub_species:
            entities += f"* {entity['singular_form']},"
            entities += f"* {entity['plural_form']},"

    query_url = f'{os.getenv("GOAT_BASE_URL")}/search?query={urllib.parse.quote(f"{query_operator}({entities})")}'
    query_url += f"&result={state['index']['classification']}"

    response = requests.get(query_url)
    response_parsed = response.json()
    return [
        {
            "taxon_id": res["result"]["taxon_id"],
            "taxon_rank": res["result"]["taxon_rank"],
            "scientific_name": res["result"]["scientific_name"],
            "taxon_names": (
                [x["name"] for x in res["result"]["taxon_names"]] if "taxon_names" in res["result"] else None
            ),
            "lineage": res["result"]["lineage"],
        }
        for res in response_parsed["results"]
    ]
