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

Queries related to **assembly** appear as follows:
1. What are the latest assemblies for the family Canidae?
2. How many genome assemblies are available for amphibians?

Queries related to **sample** appear as follows:
1. Find samples with RNA-seq data for tigers
2. Do any samples for cattle include RNA-seq data?

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

We want to identify all the entities in the query.

An entity is a word in the query that represents the subject of the query.

For example, in the query "How many bird species have been collected so far?",
the entity are "bird".

You need to return a list containing all the entities in the query along
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

The query given by the user is as follows:
`{query}`

If there are no entities in the query, return an empty list.

Return the entities in the following JSON format:
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

A rank can be one of the following:
- kingdom
- phylum
- class
- order
- family
- genus
- species

The query given by the user is as follows:
`{query}`

If rank is not applicable to the query, return an empty string and an explanation.

Return the rank in the following JSON format:
{{
    "rank": "...",
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
- **search**: The user is looking for information.
- **count**: The user is looking for a count of something.
- **record**: The user is looking for a specific record.

Examples for each intent:
- search: "What are the latest assemblies for the family Canidae?"
- count: "How many bird species have been collected so far?"
- record: "What information do we have about the African Elephant?"

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

{attribute_metadata}

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
the user has explicitly mentioned that attribute in the query.

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
