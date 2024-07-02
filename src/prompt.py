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
