from llama_index.core import PromptTemplate


QUERY_PROMPT = PromptTemplate('''We need to query a database that is exposed
by an API that has its own query syntax. I am giving you the query by the user,
you need to convert it to the API counter part. Use the examples given below as
reference:

{context_str}

------

The current date and time is {time}
Use this for any time related calculation

We have also fetched some related entities and their taxon id:
{entity_taxon_map}
Use the best matching result from this in the final output.


Query given by the user:
{query_str}

              
Return your response in a JSON of the following pattern:
{{
    "url": ""
}}
I do not want any explanation, return ONLY the json
''')

ENTITY_PROMPT = '''The following query is given by the user:

{query}

We need to make an API call using this query.
For that we need to convert all the entities in this query to their
scientific counterparts (specifically their family/species name).
For e.g. cat/fox will be translated to Felidae, elephant to Elephantidae.
Return all entities and their converted form as a single list of strings in a JSON of the following format:
{{
    "entity": ["", ""]
}}
I do not want any explanation, return ONLY the json
'''


def wrap_with_entity_prompt(query: str):
    return ENTITY_PROMPT.format(query=query)
