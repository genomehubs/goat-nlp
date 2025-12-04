"""Validation utilities for GoaT MCP server."""

from typing import Any


def validate_operator(operator: str, meta: dict) -> str:
    """Validate and return a proper GoaT operator."""
    valid_operators = {"=": "=", "!=": "!=", ">": ">", "<": "<", ">=": ">=", "<=": "<="}
    valid_kw_operators = {"=": "=", "!=": "!="}
    if meta.get("processed_type") == "keyword":
        valid_operators = valid_kw_operators
    if operator not in valid_operators:
        raise ValueError(f"Invalid operator '{operator}'. Must be one of {list(valid_operators.keys())}.")
    return valid_operators[operator]


def validate_attribute_value(value: Any, meta: dict) -> str:
    """Validate and format an attribute value for GoaT query."""
    if meta.get("processed_type", "").endswith("keyword") and meta.get("constraint", {}).get("enum"):
        valid_values = [v.lower() for v in meta["constraint"]["enum"]]
        values = [v.strip().lower() for v in str(value).split(",")]
        for v in values:
            if v.lstrip("!") not in valid_values:
                raise ValueError(f"Invalid value '{v}' for attribute. Must be one of {valid_values}.")
        return ",".join(values)
    return value


def validate_attribute_name(name: str, search_index: str, field_cache: dict) -> str:
    """Validate attribute name for GoaT query."""
    if name is None or not isinstance(name, str) or not name.strip():
        raise ValueError("Attribute name must be a non-empty string.")
    if name not in field_cache.get(search_index, {}):
        raise ValueError(f"Attribute name '{name}' not found in GoaT for index '{search_index}'.")
    return name


def validate_attribute(attr: dict, search_index: str, field_cache: dict) -> dict:
    """Validate attribute name, operator, and value for GoaT query."""
    name = validate_attribute_name(attr.get("name"), search_index, field_cache)
    meta = field_cache.get(search_index, {}).get(name, {})
    operator = attr.get("operator")
    value = attr.get("value")

    # Check for invalid pattern: using >0 or >=0 to test for presence
    if operator in (">", ">=") and value in (0, "0", 0.0, "0.0"):
        raise ValueError(
            f"Invalid filter pattern for '{name}': Using {operator}{value} to test for attribute "
            f"presence is not supported. To filter for records with any value for this attribute, "
            f"use only the attribute name without operator or value: {{\"name\": \"{name}\"}}"
        )

    if operator is not None:
        operator = validate_operator(operator, meta)
    if value is not None:
        value = validate_attribute_value(value, meta)
        if operator is None:
            operator = "="

    return {**attr, "name": name, "operator": operator, "value": value}


def validate_attributes(
    attributes: list[dict] | None,
    search_index: str,
    field_cache: dict,
) -> list[dict] | None:
    """Validate a list of attribute filters for GoaT query."""
    if not attributes:
        return None
    validated_attrs = []
    for attr in attributes:
        validated_attr = validate_attribute(attr, search_index, field_cache)
        validated_attrs.append(validated_attr)
    return validated_attrs


def validate_attribute_names(
    names: list[str] | None,
    search_index: str,
    field_cache: dict,
) -> list[str] | None:
    """Validate a list of attribute names for GoaT query."""
    if not names:
        return None
    validated_names = []
    other_names = []
    for name in names:
        try:
            validated_name = validate_attribute_name(name, search_index, field_cache)
            validated_names.append(validated_name)
        except ValueError:
            if name.endswith("_id") or name in {"scientific_name", "taxon_rank"}:
                other_names.append(name)
    return validated_names.extend(other_names) or None
