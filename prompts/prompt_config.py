QUERY_PROMPT = '''We need to query a database that is exposed by an API that has its own query syntax.
I am giving you the query by the user, you need to convert it to the API counter part. 
Ignore any id like numbers in the URL, do not guess any numbers
Use the examples given below as reference:

{query}

We DO NOT want a verbose output. Just return the final URL. Return it in a JSON of the following pattern:
{{
    "url": ""
}}
Do not return anything else
'''