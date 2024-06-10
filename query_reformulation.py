from llama_index.core import Settings
from prompt import wrap_with_entity_prompt
import os
import json
import requests
import logging

logger = logging.getLogger('goat_nlp.query_reformulation')


def fetch_related_taxons(query: str):
    """
    Fetches related taxons for a given query.

    Args:
        query (str): The query for which related taxons need to be fetched.

    Returns:
        dict: A dictionary mapping entities to their corresponding taxons.

    Raises:
        Exception: If an error occurs while making the API call to retrieve
            taxons.

    Example:
        >>> query = "find the number of assemblies for bat"
        >>> fetch_related_taxons(query)
        {'bat': ['Chiroptera', 'bat']}

    """
    entity_taxon_map = {}
    for i in range(int(os.environ.get("RETRY_COUNT", 3))):
        try:
            llm_response = Settings.llm.complete(wrap_with_entity_prompt(query))
            entities = json.loads(llm_response.text)['entity']
            logger.info(entities)
            entity_taxon_map = goat_api_call_for_taxon(entities)
            break
        except Exception:
            pass
    return entity_taxon_map


def goat_api_call_for_taxon(entities: list) -> dict:
    """
    Makes an API call to retrieve taxons for a list of entities.

    Args:
        entities (list): A list of entities for which taxons need to be
            retrieved.

    Returns:
        dict: A dictionary mapping entities to their corresponding taxons.

    Raises:
        Exception: If an error occurs while making the API call to retrieve
            taxons.

    Example:
        >>> entities = ["bat", "cat", "dog"]
        >>> goat_api_call_for_taxon(entities)
        {'bat': ['Chiroptera', 'bat'], 'cat': ['Felis', 'cat'],
            'dog': ['Canis', 'dog']}
    """
    entity_result_map = {}
    for entity in entities:
        try:
            response = requests.get(os.environ.get('GOAT_BASE_URL', 'https://goat.genomehubs.org/api/v2')
                                    + f"/lookup?searchTerm={entity}"
                                    + "&result=taxon&taxonomy=ncbi")
            json_data = response.json() if response and response.status_code == 200 else None
            entity_result_map[entity] = [x["result"] for x in json_data['results']]
        except Exception:
            pass
    return entity_result_map
