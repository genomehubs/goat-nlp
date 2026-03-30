from .validation import validate_attribute_value

# helpers/errors.py
"""Centralized error messages for LLM-facing tools."""

import urllib.parse

from ...config import ISSUE_TEMPLATE_UNHANDLED_ERROR, ISSUE_URL


class LLMError(Exception):
    """Base class for LLM-facing errors with helpful messages."""
    pass


class ToolExecutionError(LLMError):
    """Handled tool error that callers can distinguish from unexpected exceptions."""

    def __init__(self, tool_name: str, message: str):
        super().__init__(message)
        self.tool_name = tool_name
        self.message = message


# Artifact errors
def artifact_retrieval_error(artifact_type: str, tool_name: str) -> str:
    """Reusable message for invalid artifact retrieval."""
    return f"""Invalid {artifact_type}_artifact_id provided to {tool_name}().
Ensure you pass the EXACT key from process_{artifact_type}()
WITHOUT modification.

Note that artifact keys are only valid for ~5 minutes after creation.
If expired, re-run process_{artifact_type}() to get a new key."""


# Intent/operation errors
def invalid_intent_error(intent: str, valid_intents: set[str], tool_name: str) -> str:
    """Reusable message for invalid intent."""
    return f"""Invalid intent '{intent}' provided to {tool_name}().
Valid intents are: {', '.join(sorted(valid_intents))}."""


def unsupported_intent_error(intent: str, tool_name: str, suggested_tool: str) -> str:
    """Reusable message for intents that require a different tool."""
    return f"""Intent '{intent}' is not supported by {tool_name}().
Use {suggested_tool}() instead."""


# Parameter validation errors
def invalid_option_error(param_name: str, value: str, valid_options: set[str]) -> str:
    """For axis_name, scale, show_other type parameters."""
    return f"""Invalid {param_name} '{value}'.
Valid options are: {', '.join(sorted(valid_options))}."""


def invalid_attribute_error(attr_name: str, attr_type: str, valid_attrs: list[str] | set[str]) -> str:
    """For names, ranks, fields validation."""
    return f"""Invalid {attr_type} '{attr_name}'.
Valid options are: {', '.join(sorted(valid_attrs))}."""


def parsing_error(field_name: str, field_value: str, expected_format: str) -> str:
    """For format/parsing errors in axis_definition, etc."""
    return f"""Could not parse {field_name}: '{field_value}'.
Expected format: {expected_format}."""


def validation_error(tool_name: str, validation_msg: str) -> str:
    """Wrapper for general validation errors from called functions."""
    return f"""Validation error in {tool_name}(): {validation_msg}"""

# Value errors


def invalid_count_error(param_name: str, value: int, min_allowed: int = 1) -> str:
    """For bin_count, page, size validation."""
    return f"""Invalid {param_name}: {value}.
{param_name} must be {min_allowed} or greater.
Examples: {param_name}={min_allowed}, {param_name}={min_allowed * 10}"""


def invalid_range_error(
    field_name: str,
    min_value: float | None,
    max_value: float | None,
    field_meta: dict
) -> str | None:
    """Validate min/max range values against field metadata.

    Calls validate_attribute_value for numeric constraints.
    Returns error message if invalid, None if valid.
    """
    # Basic range logic errors
    if min_value is not None and max_value is not None:
        if min_value == max_value:
            return f"""Invalid range: min_value and max_value cannot be equal ({min_value}).
To filter a single value, use process_attributes() instead."""
        if min_value > max_value:
            return f"""Invalid range: min_value ({min_value}) cannot be greater than max_value ({max_value}).
Please check your values and try again."""

    if field_meta.get("type") in {"integer", "float"}:
        # Validate against field constraints using validate_attribute_value
        try:
            if min_value is not None:
                validate_attribute_value(min_value, field_meta)
            if max_value is not None:
                validate_attribute_value(max_value, field_meta)
        except ValueError as e:
            return str(e)

    return None


def format_unhandled_error_for_issue(tool_name: str, error_message: str) -> dict:
    """Format an unhandled error for user-facing response with issue reporting guidance.

    Returns a dict with:
    - user_message: Safe, friendly message to return to the user
    - issue_body: Pre-formatted issue body for bug tracking
    - issue_url: URL to issues page
    - issue_create_url: URL pre-filled with issue title and body (for convenient reporting)
    """
    # Format the issue body using the configured template
    issue_body = ISSUE_TEMPLATE_UNHANDLED_ERROR.format(
        tool_name=tool_name,
        error_message=error_message,
    )

    # Create a pre-filled GitHub issue URL
    issue_title = f"Unhandled error in {tool_name}"
    quoted_title = urllib.parse.quote(issue_title)
    quoted_body = urllib.parse.quote(issue_body)
    issue_create_url = f"{ISSUE_URL}/new?title={quoted_title}&body={quoted_body}"

    # User-facing message (doesn't expose raw error)
    user_message = (
        f"An unexpected error occurred in {tool_name}. "
        f"Please help us improve by reporting this issue."
    )

    return {
        "user_message": user_message,
        "issue_body": issue_body,
        "issue_url": ISSUE_URL,
        "issue_create_url": issue_create_url,
    }
