from llama_index.core import PromptTemplate

QUERY_PROMPT = PromptTemplate(
    """We need to parse a query given by the user.
The user is asking a genomics question, we need to parse the query into different parts.
Use the examples given below as reference:

{context_str}

------

The current date and time is {time}
Use this for any time related calculation
Change all entities from PLURAL to SINGULAR form
e.g. elephants will be converted to elephant in the output, wolves to wolf


Query given by the user:
{query_str}

------
Omit fields that are not required and remember that the examples given to you are
just basic samples, you may have to combine multiple fields to get the correct output.

Time related queries will always have the last_updated field in the time_frame_query
 part.
You can use >= and <= operators to filter such data. e.g. last_updated>=2021-01-01

------
ONLY RETURN THE JSON OF THE FOLLOWING FORMAT AND NOTHING ELSE
{{
    "taxon": "...",
    "rank": "...",
    "phrase": "...",
    "intent": "...",
    "field": "..."
    "time_frame": "...",
    "time_frame_query": "..."
    ...
}}
"""
)
