import json
import itertools
from datetime import datetime
import urllib.parse

# Define the lists of entities
taxa = ['bat', 'cat', 'gnat', 'rat', 'spider', 'Borneo magnolia', 'mushroom', 'bird',
        'rodent', 'human', 'wolf', 'fruit fly', 'Primate', 'cattle', 'fungi', 'reptile']
ranks = ['species', 'genus', 'family', 'order']
data_types = ['genome assemblies', 'RNA-seq data', 'sequencing platforms']
phrases = ['have been sequenced', 'have genome assemblies', 'have RNA-sequencing',
           'include RNA-seq data']
timeframes = ['this month', 'recently', '']

# Refined prompt templates
prompts = [
    "What {rank} of {taxon} {phrase}?",
    "How many {data_type} have been produced {timeframe}?",
    "What is the sequencing status of the {taxon}?",
    "What information do we have about {taxon}?",
    "Does {taxon} {phrase}?",
    "Which {rank} in the {taxon} {phrase}?",
    "How many {rank} of {taxon} have {data_type}?",
    "What sequencing platforms are used for {taxon} {data_type}?",
    "Do any samples for {taxon} include {data_type}?",
    "How many genome assemblies for {taxon} have been updated {timeframe}?",
    "What are the available RNA-seq platforms for the {taxon}?"
]


def generate_sample_queries():
    queries = set()
    for prompt, (rank, taxon, phrase, data_type,
                 timeframe) in itertools.product(prompts,
                                                 itertools.product(ranks, taxa, phrases,
                                                        data_types, timeframes)):
        query = prompt.format(rank=rank, taxon=taxon, phrase=phrase,
                              data_type=data_type, timeframe=timeframe).strip()
        queries.add(query)
    return list(queries)


def generate_json_output(query):
    # Define the lookup tables
    lookup_tables = {
        "taxon": taxa,
        "rank": ranks,
        "phrase": phrases,
        "data_type": data_types,
        "time_frame": timeframes
    }

    # Identify entities in the query
    output = {key: next((item for item in items if item in query),
                        None) for key,
                        items in lookup_tables.items() if next((item for item in items if item in query), None)}

    # Determine the intent
    if query.lower().startswith("how many"):
        output["intent"] = "count"
    elif query.lower().startswith("list all") or query.lower().startswith("find samples"):
        output["intent"] = "search"
    elif query.lower().startswith("what information do we have about"):
        output["intent"] = "record"
    else:
        output["intent"] = "search"

    # Map phrases to fields
    phrase_to_field = {
        "have been sequenced": "assembly_span",
        "have genome assemblies": "assembly_span",
        "have RNA-sequencing": "sra_accession",
        "include RNA-seq data": "sra_accession"
    }

    if "phrase" in output and output["phrase"] in phrase_to_field:
        output["field"] = phrase_to_field[output["phrase"]]
    
    if "data_type" in output:
        data_type_to_field = {
            "genome assemblies": "assembly_span",
            "RNA-seq data": "sra_accession",
            "sequencing platforms": "platform"
        }
        output["field"] = data_type_to_field[output["data_type"]]
    
    time_frame_to_query = {
        "this month": "last_updated>={}".format(datetime.now().replace(day=1).strftime('%Y-%m-%d')),
        "recently": "last_updated>=recent",  # Adjust this logic as per your specific definition of "recently"
        # Add more specific time frame mappings as needed
    }

    if "time_frame" in output and output["time_frame"] in time_frame_to_query:
        output["time_frame_query"] = time_frame_to_query[output["time_frame"]]
    
    return output


def construct_url(json_output):
    base_url = "https://goat.genomehubs.org/"
    endpoint = "search?"

    if json_output['intent'] == 'count':
        endpoint = "count?"
    elif json_output['intent'] == 'record':
        endpoint = "record?"

    params = []

    if 'taxon' in json_output:
        params.append(f"tax_tree(* {json_output['taxon']})")
    if 'rank' in json_output:
        params.append(f"tax_rank({json_output['rank']})")
    if 'field' in json_output:
        params.append(f"{json_output['field']}")
    if "time_frame_query" in json_output:
        params.append(f"{json_output['time_frame_query']}")

    query_string = " AND ".join(params)
    return base_url + endpoint + "query=" + urllib.parse.quote_plus(query_string) + "&result=taxon&summaryValues=count&taxonomy=ncbi&offset=0&fields=assembly_level%2Cassembly_span%2Cgenome_size%2Cchromosome_number%2Chaploid_number&names=common_name&ranks=&includeEstimates=false&size=100"


sample_queries = generate_sample_queries()
output_list = []
for query in sample_queries:  
    json_output = generate_json_output(query)
    url = construct_url(json_output)
    output_list.append({
        "english_query": query,
        "json_output": json_output,
        "api_query": url
    })


with open('sample_queries_output.json', 'w') as outfile:
    json.dump(output_list, outfile, indent=2)