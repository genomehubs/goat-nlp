from datetime import datetime

from llama_index.core import Settings

from prompt import JSON_RETRY_PROMPT, JSON_VALIDATION_PROMPT


def validate_json_query_conditions(previous_json_output: dict, user_query: str):
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
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    populated_prompt = JSON_RETRY_PROMPT.format(
        json_output=previous_json_output,
        user_query=user_query,
        reason=reason,
        time=current_time,
    )
    response = Settings.llm.complete(populated_prompt)
    return str(response)
