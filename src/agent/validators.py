from datetime import datetime

from llama_index.core import Settings

from prompt import JSON_RETRY_PROMPT, JSON_VALIDATION_PROMPT


def validate_json_query_conditions(previous_json_output: dict, user_query: str):
    """

    This tool HAS to be called after the query is parsed and a JSON object is created.
    This tool validates the JSON against the original query.
    The tool will return a JSON object with a 'valid' key that
     will be True if the JSON is correct and False otherwise.

    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    populated_prompt = JSON_VALIDATION_PROMPT.format(
        json_output=previous_json_output,
        user_query=user_query,
        time=current_time,
    )
    response = Settings.llm.complete(populated_prompt)
    return str(response)


def correct_json_query_conditions(
    previous_json_output: dict, user_query: str, reason: str
):
    """

    This tool HAS to be called only after the query is validated and valid is False.
    This tool corrects the incorrect JSON based on the reason provided.
    The tool will return a JSON object with a 'valid' key that will be
     True if the JSON is correct and False otherwise.

    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    populated_prompt = JSON_RETRY_PROMPT.format(
        json_output=previous_json_output,
        user_query=user_query,
        reason=reason,
        time=current_time,
    )
    response = Settings.llm.complete(populated_prompt)
    return str(response)
