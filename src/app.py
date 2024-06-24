import json
import logging
import os
import sys
import urllib

from flask import Flask, render_template, request

from index import load_index, query_engine

app = Flask("goat_nlp")

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)


def construct_url(json_output):
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


def chat_bot_rag(query):
    # entity_taxon_map = fetch_related_taxons(query)
    for _ in range(int(os.getenv("RETRY_COUNT", 3))):
        try:
            model_response = json.loads(query_engine.custom_query(query))
            return {
                "json_debug": json.dumps(model_response, indent=2),
                "url": construct_url(model_response),
            }
            # return construct_url(json.loads(query_engine.custom_query(query)))
        except Exception as e:
            app.logger.error(f"Error: {e}")
            app.logger.error("Retrying...")
    model_response = json.loads(query_engine.custom_query(query))
    return {
        "json_debug": json.dumps(model_response, indent=2),
        "url": construct_url(model_response),
    }


@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/rebuildIndex")
def index():
    load_index(force_reload=True)


@app.route("/chat", methods=["POST"])
def chat():
    return chat_bot_rag(request.form["user_input"])


if __name__ == "__main__":
    app.run(debug=True)
