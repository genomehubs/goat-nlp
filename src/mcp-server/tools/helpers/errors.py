# helpers/errors.py
"""Centralized error messages for LLM-facing tools."""


class LLMError(Exception):
    """Base class for LLM-facing errors with helpful messages."""
    pass


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
