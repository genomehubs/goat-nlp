from llama_index.core import PromptTemplate

INDEX_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.
We want to classify the query into one of the three types:
- **taxon**
- **assembly**
- **sample**

There are 3 indices: **taxon**, **assembly**, and **sample**.

Queries related to **taxon** appear as follows:
1. How many bird species have been collected so far?
2. What mushroom species have RNA seq?
3. What is the distribution of assembly span values across the phylum Chordata?

Queries related to **assembly** appear as follows:
1. What are the latest assemblies for the family Canidae?
2. How many genome assemblies are available for amphibians?

Queries related to **sample** appear as follows:
1. Find samples with RNA-seq data for tigers
2. Do any samples for cattle include RNA-seq data?

A query looking for values across a taxonomic group that does not mention "assemblies" is most likely to be related
to the taxon index.

Classify the following query into one of the three types:
`{query}`

Return the classification in the following JSON format:
{{
"classification": "taxon or assembly or sample",
"explanation": "..."
}}

The classification key in your response SHOULD HAVE ONLY ONE OF THE THREE VALUES.
You CANNOT reply with a combination of any values.
e.g. "classification": "taxon, assembly", "classification": "taxon/assembly" etc.
IS NOT ALLOWED.

```json

"""
)

ENTITY_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.

We want to identify all the taxa in the query.

A taxon is a living organism present as the subject of the query.

For example:
- in the query "How many bird species have been collected so far?", the taxon is "bird".
- in the query "give me a tree of ant families", the taxon is "ant".
- in the query "show me the genome sizes for all species of elephant, cat and yeast?",
  there are 3 taxa, "elephant, cat, and yeast".

The query may refer to a subset of a larger group of organisms, for example in
the query "What are the latest assemblies for the bivalve molluscs?", the taxon
is Bivalvia and **NOT** Mollusca.

These queries have no taxa:
- "what is the distribution of genome sizes across all classes?"
- "How many samples are there in total?"

The identified taxa *HAVE TO BE* living organisms but should not be a group of
organisms based on taxonomic rank alone.

You need to return a list containing all the taxa in the query along
with their singular/plural forms and scientific names.

For example, for the query "How many bird species have been collected so far?",
the output would be:
```
[
    {{
        "singular_form": "bird",
        "plural_form": "birds",
        "scientific_name": "Aves"
    }}
]
```

If taxa is not applicable to the query, return an empty list.

The query given by the user is as follows:
`{query}`

Return the taxa as a list of entities in the following JSON format:
{{
    "entities": [
        {{
            "singular_form": "...",
            "plural_form": "...",
            "scientific_name": "..."
        }}
    ],
    "explanation": "..."
}}

```json
"""
)

RANK_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.

We want to identify the rank at which the query will be performed.

A rank is the position of an entity in the taxonomic hierarchy.

We have already queried the database against the user's query.

*Database Results:*
`{results}`

*User Query:*
`{query}`

Look at the results and decide wisely which rank applies to the given query.

You need to consider the following 3 important parameters while deciding the rank:
1. User Query - Find the rank that is *mentioned* in the query. For example,
    If the query is "Which species of the dog family do we know about?", the rank will be "species"
    since it is more specific than family and is mentioned in the query.
2. Results - The results contain all possible answers. You need to select the most relevant one from them.
3. Lineage - The lineage of every entry in the result is an array that contains all parents of the entry.
    Make sure that the entry that you select contains correct parents in the lineage.


You need to return the rank and the taxon id of the most relevant entry from the results.

If rank is not applicable to the query, return an empty string
for the rank and taxon_id field.

Return the rank in the following JSON format:
{{
    "rank": "...",
    "taxon_id": "...",
    "explanation": "..."
}}

```json
"""
)

LINEAGE_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.

We have already fetched results from the database for the user's query.

The query given by the user is as follows:
`{query}`

The *LINEAGE* of the most relevant taxon is as follows:
`{lineage}`

You need to identify 1 entry in the lineage that should be used to answer the query.

For e.g. if the user asks for all species of the cat family, the entry that you pick
from the lineage should be "Felidae" because it corresponds to the family rank and will contain
all the species in its descendants.

Formally speaking, you need to return the taxon id of 1 entry from the lineage that will act
as the first common ancestor of all the results that the user is looking for.

Return the taxon id in the following JSON format:
{{
    "taxon_id": "...",
    "explanation": "..."
}}

```json
"""
)

TIME_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.

We need to identify any time related information in the query.

The current date time is: {time}

The query given by the user is as follows:
`{query}`

You need to return a JSON containing the requested time in YYYY-MM-DD format.
The JSON has to be in the following format:
{{
    "from_date": "YYYY-MM-DD",
    "to_date": "YYYY-MM-DD",
    "explanation": "..."
}}

If there is no time related information in the query, return an empty string
for both from_date and to_date.
If 'from' is not applicable, return an empty string for from_date.
If 'to' is not applicable, return an empty string for to_date.

```json
"""
)

INTENT_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.

We need to identify the intent of the query.

An intent can be one of the following three types:
- **search**: The user is looking for a table of values.
- **count**: The user is looking for a count of something.
- **record**: The user is looking for a specific taxon, assembly or sample record.
- **tree**: The user is looking for a phylogenetic tree.
- **histogram**: The user is looking for a histogram chart showing the distribution of a **SINGLE** attribute.
- **scatter**: The user is looking for a scatter plot chart showing the distribution of a pair of attributes.

Examples for each intent:
- search: "What are the latest assemblies for the family Canidae?"
- search: "What are the gene counts for squirrel and mouse assemblies?
- search: "What are the assembly span values for pine and spruce assemblies?
- count: "How many bird species have been collected so far?"
- record: "What information do we have about the African Elephant?"
- tree: "Show me a tree of all families in the phylum chordata"
- histogram: "What is the distribution of assembly span for species in the cat family?"
- scatter: "What is the relationship between contig scaffold n50 for all domestic dog assemblies"

**REMEMBER:**
- A user only ants a distribution of values if they use the word "distribution" or "histogram" in their query.
- A user is more likely to want a scatter plot than a histogram if the query refers to a relationship
  between attributes.

The query given by the user is as follows:
`{query}`

Return the intent in the following JSON format:
{{
    "intent": "...",
    "explanation": "..."
}}

```json
"""
)

ATTRIBUTE_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.

We need to identify any attributes in the query.

These attributes might have some conditions mentioned on them
or they might simply be a "required" field in the output.

The list of possible attributes and their types/values are as follows:

`{attribute_metadata}`

The query given by the user is as follows:
`{query}`

You need to return a list of attributes present in the query along
 with the conditions mentioned on them.
The conditions can be one of the following:
>, <, >=, <=, =, !=, in

If the condition is "in", the value will be a list of values.
You need to reply in the following format:
{{
    "attributes": [
        {{
            "attribute": "...",
            "condition": "...",
            "value": "..." or ["...", "..."]
        }}
    ],
    "explanation": "..."
}}

If there are no attributes in the query, return an empty list.


**REMEMBER:** The attributes list in your response must be filled **ONLY** if
the user has **explicitly** mentioned that attribute in the query.

This means that "ebp_date" (or any other attribute) will not be included in
the list unless the phrase "ebp_date" is given in the query by the user.

**DO NOT** assume that an attribute is **IMPLIED** in the query.
**IN MOST CASES, YOUR RESPONSE WILL BE AN EMPTY LIST.**

```json
"""
)

RECORD_PROMPT = PromptTemplate(
    """
You are an intelligent assistant who **ONLY ANSWERS IN JSON FORMAT**.

A user is trying to query a genomics database.

We have already queried the database against the user's query.

We have a set of results from the database, we need to pick the best match.

Make sure that the "rank" of your answer should be the closest match to the user's query.

The query by the user is as follows:
`{query}`

The results from the database are as follows:
{results}

You need to return the best taxon from the results in the following JSON format:
{{
    "taxon_id": "...",
    "explanation": "..."
}}

The taxon_id HAS TO BE AN INTEGER.

```json
"""
)
