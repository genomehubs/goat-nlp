import json
import urllib

import requests
from llama_index.core import Settings
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata

from agent.validators import (
    correct_json_query_conditions,
    validate_json_query_conditions,
)
from index import query_engine
from prompt import BEST_URL_PROMPT


def construct_url(
    json_output: dict,
    tax_query: str,
    taxon: str,
):
    base_url = "https://goat.genomehubs.org/"
    endpoint = "search?"
    suffix = (
        "&result=taxon&summaryValues=count&taxonomy=ncbi&offset=0"
        + "&fields=assembly_level%2Cassembly_span%2Cgenome_size%2C"
        + "chromosome_number%2Chaploid_number&names=common_name&ranks="
        + "&includeEstimates=false&size=100"
    )

    if json_output["intent"] == "count":
        endpoint = "api/v2/count?"
    elif json_output["intent"] == "record":
        endpoint = "record?"

    params = []

    if "taxon" in json_output:
        params.append(tax_query.format(taxon))
    if "rank" in json_output:
        params.append(f"tax_rank({json_output['rank']})")
    if "field" in json_output:
        params.append(f"{json_output['field']}")
    if "time_frame_query" in json_output:
        params.append(f"{json_output['time_frame_query']}")
        suffix = (
            "&result=assembly&summaryValues=count&taxonomy=ncbi&offset=0"
            + "&fields=assembly_level%2Cassembly_span%2Cgenome_size%2C"
            + "chromosome_number%2Chaploid_number&names=common_name&ranks="
            + "&includeEstimates=false&size=100"
        )

    query_string = " AND ".join(params)
    return base_url + endpoint + "query=" + urllib.parse.quote(query_string) + suffix


def get_best_url(input: dict):
    """

    This tool should be called towards the END.
    It constructs a set of URLs from the JSON output of the previous tool.
    The input to this tool should be as follows:
    {"input": {"taxon": "...", ...}}

    """
    tax_options = ["tax_tree(* {})", "tax_tree({})", "tax_name({})", "tax_name(* {})"]
    urls = []
    for tax_query in tax_options:
        for taxon in [
            input["singular_form_taxon"],
            input["plural_form_taxon"],
            input["scientific_form_taxon"],
        ]:
            urls.append(construct_url(input, tax_query, taxon))

    print("calling pick_best_url")
    pick_best_url(input, urls)
    return urls


def call_api_and_filter_response(url: str):
    response = requests.get(url)
    response_parsed = response.json()
    if not response_parsed["success"]:
        return {
            "success": False,
            "error": response_parsed["error"],
        }
    filtered_response = {}
    filtered_response["hits"] = response_parsed["status"]["hits"]
    filtered_response["results"] = []
    for result in response_parsed["results"]:
        filtered_result = {}
        filtered_result["taxon_rank"] = result["taxon_rank"]
        filtered_response["scientific_name"] = result["scientific_name"]
        filtered_response["names"] = result["names"]
        filtered_response["fields"] = result["fields"].keys()
    return filtered_response


def pick_best_url(input: dict, urls: list[str]):
    """

    This tool should be called at the VERY END.
    This tool picks the best URL from the list of URLs.
    You also need to pass the original user query to this tool.

    """
    url_response_dict = {url: call_api_and_filter_response(url) for url in urls}

    print("Inside pick_best_url")
    response = Settings.llm.complete(
        BEST_URL_PROMPT.format(
            url_responses=json.dumps(url_response_dict, indent=4),
            user_query=json.dumps(input, indent=4),
        )
    )

    return response


query_engine_tools = [
    FunctionTool.from_defaults(get_best_url),
    FunctionTool.from_defaults(correct_json_query_conditions),
    FunctionTool.from_defaults(validate_json_query_conditions),
    QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="construct_json_from_query",
            description=(
                "This tool parses the user query and converts it into a JSON format"
                " by looking at similar previous examples."
                "This step HAS to be completed before constructing the final URL."
                "Just pass the raw user query as input to this tool."
            ),
        ),
    ),
]
