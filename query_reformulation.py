from llama_index.core import Settings
from prompt import wrap_with_entity_prompt
import os
import json
import requests


def fetch_related_taxons(query: str):
    entity_taxon_map = {}
    for i in range(int(os.environ["RETRY_COUNT"])):
        try:
            llm_response = Settings.llm.complete(
                wrap_with_entity_prompt(query))
            print(llm_response)
            entities = json.loads(llm_response.text)['entity']
            print(entities)
            entity_taxon_map = goat_api_call_for_taxon(entities)
            break
        except Exception:
            pass
    return entity_taxon_map


def goat_api_call_for_taxon(entities: list):
    entity_result_map = {}
    for entity in entities:
        try:
            response = requests.get(os.environ['GOAT_BASE_URL']
                                    + f"/lookup?searchTerm={entity}"
                                    + "&result=taxon&taxonomy=ncbi")
            json_data = response.json() if response and response.status_code == 200 else None
            entity_result_map[entity] = [x["result"] for x in json_data['results']]
        except Exception:
            pass
    return entity_result_map
