import urllib

from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata

from agent.validators import (
    correct_json_query_conditions,
    validate_json_query_conditions,
)
from index import query_engine


def construct_url(
    input: dict,
):
    json_output = input
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
        params.append(f"tax_tree(* {json_output['taxon']})")
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


query_engine_tools = [
    FunctionTool(
        fn=construct_url,
        metadata=ToolMetadata(
            name="construct_url",
            description=(
                "This tool should be called at the VERY END."
                "This tool constructs a URL from the JSON output of the previous tool."
                'Sample input to this tool: {\ninput: \n{\n  "taxon": "bat", ...\n}\n}'
            ),
        ),
    ),
    FunctionTool(
        fn=correct_json_query_conditions,
        metadata=ToolMetadata(
            name="correct_json_query_conditions",
            description=(
                "This tool HAS to be called only after the query is validated"
                "and valid is False."
                "This tool corrects the incorrect JSON based on the reason provided."
                "The input has to be a JSON string that can be parsed"
                " using json.loads() function."
                'Sample input to this tool: {"previous_json_output":\n{\n'
                '  "taxon": "bat", ...\n},\n"user_query": "", "reason": ""\n}'
                "The tool will return a JSON object with a 'valid' key that will be"
                " True if the JSON is correct and False otherwise.",
            ),
        ),
    ),
    FunctionTool(
        fn=validate_json_query_conditions,
        metadata=ToolMetadata(
            name="validate_json_query_conditions",
            description=(
                "This tool HAS to be called after the query is parsed and a JSON object"
                " is created."
                "This tool validates the JSON against the original query."
                'Sample input to this tool: {"previous_json_output":\n{\n  '
                '"taxon": "bat", ...\n},\n"user_query": ""\n}'
                "The tool will return a JSON object with a 'valid' key that"
                " will be True if the JSON is correct and False otherwise."
            ),
        ),
    ),
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
