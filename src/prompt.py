from llama_index.core import PromptTemplate

QUERY_PROMPT = PromptTemplate(
    """We need to parse a query given by the user.
The user is asking a genomics question, we need to parse the query into different parts.
Use the examples given below as reference:

{context_str}

------

The current date and time is {time}
Use this for any time related calculation


Query given by the user:
{query_str}

------
Omit fields that are not required and remember that the examples given to you are
just basic samples, you may have to combine multiple fields to get the correct output.

Time related queries will always have the last_updated field in the time_frame_query
 part.
You can use >= and <= operators to filter such data. e.g. last_updated>=2021-01-01

------

ADD THREE NEW FIELDS IN THE JSON (These may not be present in the examples):
1. "singular_form_taxon": "bat"
2. "plural_form_taxon": "bats"
3. "scientific_form_taxon": "Chiroptera"

------
ONLY RETURN THE JSON IN THE FOLLOWING FORMAT AND NOTHING ELSE
{{
    "taxon": "...",
    "rank": "...",
    "phrase": "...",
    "intent": "...",
    "field": "...",
    "singular_form_taxon": "...",
    "plural_form_taxon": "...",
    "scientific_form_taxon": "..."
    "time_frame": "...",
    "time_frame_query": "..."
    ...
}}

```json
"""
)

JSON_VALIDATION_PROMPT = PromptTemplate(
    """We are trying to parse a query given by the user.
    The user is asking a genomics question, we need to parse the query into different
    parts. A previous step has ALREADY parsed the query into a JSON format.
    You need to verify if all the conditions mentioned in the prompt are captured
    in the JSON. You do not need to change the JSON output, just validate it.
    If you think that the JSON is incorrect at any place, just mention the
    reason behind your logic. Check if the identified entity is correct.
    Is the time frame query correct? Is the intent correctly identified?

    current date and time is {time}

    Query given by the user: {user_query}

    JSON output: {json_output}

    Your output HAS to be in the following JSON format:
    {{
        "valid": true/false,
        "reason": "..."
    }}

    ----
    ```json
    """,
)

JSON_RETRY_PROMPT = PromptTemplate(
    """You had previously parsed a user query and converted it to a JSON.
    However, the JSON output was incorrect. You need to correct the JSON output.

    Previous JSON response:
    {json_output}

    Issues:
    {reason}

    The user query is: {user_query}
    The current date and time is {time}

    Fix and return the new JSON:

    ----
    ```json

    """,
)

BEST_URL_PROMPT = PromptTemplate(
    """
We are in the process of converting a query (related to genomics) given by a user,
to a relevant goat genomehubs API URL.

We have shortlisted a bunch of URLs based on the user query.
All of these URLs were tested and their responses are attached here.

Being an expert in genomics, you need to select the best URL from the list.
While selecting the best URL, you need to consider the following:
1. The response should have good quality results.
2. The entities in the response should be the closest match to the user query.
3. The API call should be successful. (this can be checked by looking at the
 success key).

If all API calls are unsuccessful, reply as follows:
'The API calls were unsuccessful. Please reconsider the query and try again.'

User query:
{user_query}

URLs and their responses:
{url_responses}

------
Once you have identified the best URL, reply with JUST A SINGLE BEST URL.
"""
)

AGENT_SYSTEM_PROMPT = """
You are an intelligent assistant who is very well versed with genomics.
Users come to you with a variety of questions related to genomics.
You parse the query using a set of tools and generate a URL pointing to
 an API service called goat genomehubs.

## Tools
You have access to a wide variety of tools. You are responsible for using
the tools in any sequence you deem appropriate to complete the task at hand.
This may require breaking the task into subtasks and using different tools
to complete each subtask.

You have access to the following tools:
{tool_desc}



## Output Format
Please answer in the following format:

```
Thought: I need to use a tool to help me answer the question.
Action: tool name (one of {tool_names}) if using a tool.
Action Input: the input to the tool, in a JSON format representing the kwargs
 (e.g. {{"kwarg1": "hello world", "kwarg2": 5}})
```

Please ALWAYS start with a Thought.

Please use a valid JSON format for the Action Input. Do NOT do this
 {{'input': 'hello world', 'num_beams': 5}}.

If this format is used, the user will respond in the following format:

```
Observation: tool response
```

You should keep repeating the above format until you have enough information
to answer the question without using any more tools. At that point, you MUST respond
in the one of the following two formats:

```
Thought: I have all the information and do not need to use any more tools.
 I have verified that all conditions from the user query are satisfied
   and used the get_best_url tool.
Answer: [your answer here (final goat genomehubs URL)]
```

```
Thought: I cannot answer the question with the provided tools.
Answer: [Reason behind not being able to answer the question]
```

## USUAL TOOL FLOW:
1. construct_json_from_query
2. validate_json_query_conditions
3. correct_json_query_conditions
4. get_best_url

## Current Conversation
Below is the current conversation consisting of interleaving human and
 assistant messages.

"""

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
"classification": "taxon/assembly/sample",
"explanation": "..."
}}

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
    {
        "singular_form": "bird",
        "plural_form": "birds",
        "scientific_name": "Aves"
    }
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

```json
"""
)
