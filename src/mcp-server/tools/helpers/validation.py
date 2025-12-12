"""Validation utilities for GoaT MCP server."""

import hashlib
import json

# import secrets
from typing import Any

from ...logging_config import get_logger

logger = get_logger(__name__)

SALT_FOR_HASHING = "FIXED_FOR_DEBUGGING"  # secrets.token_urlsafe(32)


def validate_modifier(modifier: str | list[str], meta: dict, search_index: str) -> str | list[str]:
    """Validate modifier(s) against attribute metadata.

    Supports both a single modifier (string) or multiple modifiers (list).
    If a list is provided, typically one status modifier + one summary modifier.
    Also handles comma-separated strings like "min, direct" and auto-converts to list.

    Args:
        modifier: The modifier (string, comma-separated string, or list of modifiers)
        meta: Attribute metadata from FIELD_CACHE
        search_index: The search index (taxon, assembly, sample)

    Returns:
        The validated modifier(s) as string or list

    Raises:
        ValueError: If any modifier is invalid for this attribute/index combination
    """
    if modifier is None:
        return None

    # Handle comma-separated string: "min, direct" → ["min", "direct"]
    if isinstance(modifier, str) and "," in modifier:
        modifier = [m.strip() for m in modifier.split(",") if m.strip()]

    # Handle both single modifier (string) and multiple modifiers (list)
    modifiers_to_check = [modifier] if isinstance(modifier, str) else modifier

    # Determine valid modifiers from metadata
    summary_mods = list(meta.get("summary", []))
    if "list" in summary_mods:
        summary_mods.append("length")
    if "primary" in summary_mods:
        summary_mods.remove("primary")  # Remove 'primary' if present

    valid_modifiers = {"missing", "direct", "ancestral", "descendant", "estimated"} | set(summary_mods)
    for m in modifiers_to_check:
        if m not in valid_modifiers:
            raise ValueError(f"Invalid modifier '{m}'. Must be one of {valid_modifiers}.")

    # "missing" is always valid for any attribute
    if "missing" in modifiers_to_check:
        return modifier  # Return as-is

    # Check status modifiers (direct, ancestral, descendant, estimated)
    status_modifiers = {m for m in modifiers_to_check if m in {"direct", "ancestral", "descendant", "estimated"}}
    for status_mod in status_modifiers:
        if status_mod in {"ancestral", "estimated"}:
            if search_index != "taxon":
                raise ValueError(
                    f"Modifier '{status_mod}' is only valid for taxon index, not {search_index}."
                )
            traverse_direction = meta.get("traverse_direction")
            if status_mod == "ancestral":
                if traverse_direction not in {"down", "both"}:
                    raise ValueError(
                        f"Modifier 'ancestral' not valid for '{meta.get('name', 'unknown')}': "
                        f"traverse_direction is {traverse_direction}, needs 'down' or 'both'."
                    )
            elif status_mod == "estimated":
                if traverse_direction is None:
                    raise ValueError(
                        f"Modifier 'estimated' not valid for '{meta.get('name', 'unknown')}': "
                        f"traverse_direction is None."
                    )
        elif status_mod == "descendant":
            if search_index != "taxon":
                raise ValueError(
                    f"Modifier 'descendant' is only valid for taxon index, not {search_index}."
                )
            traverse_direction = meta.get("traverse_direction")
            if traverse_direction not in {"up", "both"}:
                raise ValueError(
                    f"Modifier 'descendant' not valid for '{meta.get('name', 'unknown')}': "
                    f"traverse_direction is {traverse_direction}, needs 'up' or 'both'."
                )
        elif status_mod == "direct":
            if search_index != "taxon":
                raise ValueError(
                    f"Modifier 'direct' is only valid for taxon index, not {search_index}."
                )

    # Check summary modifiers (min, max, median, length)
    summary_modifiers = {m for m in modifiers_to_check if m in {"min", "max", "median", "length"}}
    for summary_mod in summary_modifiers:
        if summary_mod in {"min", "max", "median"}:
            summary = meta.get("summary")
            if summary is None or summary_mod not in summary:
                raise ValueError(
                    f"Modifier '{summary_mod}' not valid for '{meta.get('name', 'unknown')}': "
                    f"this attribute does not support a {summary_mod} summary."
                )
        elif summary_mod == "length":
            processed_type = meta.get("processed_type", "")
            if processed_type != "keyword":
                raise ValueError(
                    f"Modifier 'length' is only valid for keyword (list) attributes, "
                    f"not '{meta.get('name', 'unknown')}' (type: {processed_type})."
                )

    return modifier


def validate_operator(operator: str, meta: dict) -> str:
    """Validate and return a proper GoaT operator."""
    if operator is None or not isinstance(operator, str) or not operator.strip():
        return None
    valid_operators = {
        "=": "=",
        "!=": "!=",
        ">": ">",
        "<": "<",
        ">=": ">=",
        "<=": "<=",
        "==": "=",
        "eq": "=",
        "equals": "=",
        "equal": "=",
        "is": "=",
        "in": "=",
        "contains": "=",
        "contains any": "=",
        "!=": "!=",
        "<>": "!=",
        "not": "!=",
        "neq": "!=",
        "not equals": "!=",
        "not equal": "!=",
        "is not": "!=",
        "not in": "!=",
        "excludes": "!=",
        "does not contain": "!=",
        "doesn't contain": "!=",
        "exists": "exists",
        "status": "exists",
        "missing": "missing",
        "not exists": "missing",
        "!exists": "missing",
    }
    if meta.get("processed_type") != "keyword":
        valid_operators |= {
            ">": ">",
            "<": "<",
            ">=": ">=",
            "<=": "<=",
            "greater than": ">",
            "less than": "<",
            "greater than or equal to": ">=",
            "less than or equal to": "<=",
        }
    if operator.lower() not in valid_operators:
        raise ValueError(f"Invalid operator '{operator}'. Must be one of {list(valid_operators.keys())}.")
    return valid_operators[operator.lower()]


def validate_attribute_value(value: Any, meta: dict) -> str:
    """Validate and format an attribute value for GoaT query."""
    if meta.get("processed_type", "").endswith("keyword") and meta.get("constraint", {}).get("enum"):
        valid_values = [v.lower() for v in meta["constraint"]["enum"]]
        if isinstance(value, str):
            values = [v.strip().lower() for v in value.split(",")]
        elif isinstance(value, list):
            values = [str(v).strip().lower() for v in value]
        for v in values:
            if v.lstrip("!") not in valid_values:
                raise ValueError(f"Invalid value '{v}' for attribute. Must be one of {valid_values}.")
        return "%2C".join(values)
    return value


def validate_attribute_name(name: str, search_index: str, field_cache: dict) -> str:
    """Validate attribute name for GoaT query."""
    if name is None or not isinstance(name, str) or not name.strip():
        raise ValueError("Attribute name must be a non-empty string.")
    if name not in field_cache.get(search_index, {}):
        raise ValueError(f"Attribute name '{name}' not found in GoaT for index '{search_index}'.")
    return name


def validate_attribute(attr: dict, search_index: str, field_cache: dict) -> dict:
    """Validate attribute name, operator, value, and modifier for GoaT query.

    Also preserves modifier field if present for backend processing.
    Valid modifiers: "missing", "direct", "ancestral", "descendant", "estimated", "min", "max", "median", "length"
    """
    name = attr.get("name")
    if name is None:
        raise ValueError("Attribute dictionary must have a 'name' field.")
    parts = name.split(":")
    name = parts[0]
    modifier = attr.get("modifier")
    if len(parts) > 1:
        if modifier is not None:
            raise ValueError(f"Attribute '{name}' has modifier specified both in name "
                             f"({parts[1]}) and modifier field ({modifier}).")
        modifier = parts[1]
    name = validate_attribute_name(name, search_index, field_cache)
    meta = field_cache.get(search_index, {}).get(name, {})
    operator = attr.get("operator")
    value = attr.get("value")

    # Check for invalid pattern: using >0 or >=0 to test for presence
    if operator in {">", ">="} and isinstance(value, (int, float)) and value == 0:
        raise ValueError(
            f"Invalid filter pattern for '{name}': Using {operator}{value} to test for attribute "
            f"presence is not supported. To filter for records with any value for this attribute, "
            f"use only the attribute name without operator or value: {{\"name\": \"{name}\"}}, "
            f"or use the 'exists' operator: {{\"name\": \"{name}\", \"operator\": \"exists\"}}."
        )

    if operator is not None:
        if (
            (isinstance(value, str) and value in {"ancestral", "descendant", "estimated", "direct", "missing"})
            or (isinstance(value, list) and all(v in {"ancestral", "descendant", "estimated", "direct", "missing"} for v in value))
        ):
            modifier = value
            operator = None
            value = None
        elif operator.lower() == "exists":
            operator = None
            value = None
        elif operator.lower() == "missing":
            operator = None
            value = None
            modifier = "missing"
        else:
            operator = validate_operator(operator, meta)
    if value is not None:
        value = validate_attribute_value(value, meta)
        if operator is None:
            operator = "="

    # Validate modifier if present
    if modifier is not None:
        # Handle both single modifier (string) and multiple modifiers (list)
        if isinstance(modifier, list):
            modifier = [validate_modifier(m, meta, search_index) for m in modifier]
        else:
            modifier = validate_modifier(modifier, meta, search_index)

    validated = {**attr, "name": name, "operator": operator, "value": value}
    # Preserve modifier if present
    if modifier is not None:
        validated["modifier"] = modifier
    return validated


def validate_attributes(
    attributes: list[dict] | None,
    search_index: str,
    field_cache: dict,
    is_field: bool = False,
) -> list[dict] | None:
    """Validate a list of attribute filters for GoaT query.

    Special validation: Detects if same attribute appears multiple times with
    summary modifiers (min/max) on one and status modifiers (direct/ancestral)
    on another, and raises error instructing to combine them in one dict.
    """
    if not attributes:
        return None

    # Check for split summary+status modifiers pattern
    attr_by_name = {}
    for attr in attributes:
        name = attr.get("name")
        if name not in attr_by_name:
            attr_by_name[name] = []
        attr_by_name[name].append(attr)

    # If same attribute appears multiple times, check if modifiers should be combined
    for name, attrs in attr_by_name.items():
        if len(attrs) > 1:
            # Check each pair of attributes with same name
            for i, attr1 in enumerate(attrs):
                for attr2 in attrs[i+1:]:
                    mod1 = attr1.get("modifier")
                    mod2 = attr2.get("modifier")

                    if mod1 is None or mod2 is None:
                        continue

                    # Flatten to lists
                    mods1 = [mod1] if isinstance(mod1, str) else mod1
                    mods2 = [mod2] if isinstance(mod2, str) else mod2

                    # Check if one has summary and other has status
                    summary_set = {"min", "max", "median", "length"}
                    status_set = {"missing", "direct", "ancestral", "descendant", "estimated"}

                    summary1 = [m for m in mods1 if m in summary_set]
                    status1 = [m for m in mods1 if m in status_set]
                    summary2 = [m for m in mods2 if m in summary_set]
                    status2 = [m for m in mods2 if m in status_set]

                    # Error only if:
                    # - One dict has ONLY summary modifier(s) and other has ONLY status modifier(s)
                    # - AND they have the same summary modifier (e.g., both "min")
                    # This catches: [{modifier: "min"}, {modifier: "direct"}]
                    # But allows: [{modifier: ["min", "direct"]}, {modifier: ["max", "direct"]}]
                    if summary1 and status2 and not status1 and not summary2:
                        if summary1 == summary2:  # Same summary modifier split
                            raise ValueError(
                                f"ERROR: Attribute '{name}' appears twice with split modifiers.\n"
                                f"Found: summary modifier '{summary1[0]}' in one dict "
                                f"AND status modifier '{status2[0]}' in another.\n"
                                f"These MUST be combined in ONE dict:\n"
                                f"  {{\n"
                                f"    \"name\": \"{name}\",\n"
                                f"    \"modifier\": [\"{summary1[0]}\", \"{status2[0]}\"]\n"
                                f"  }}\n"
                            )
                    elif summary2 and status1 and not status2 and not summary1:
                        if summary2 == summary1:  # Same summary modifier split
                            raise ValueError(
                                f"ERROR: Attribute '{name}' appears twice with split modifiers.\n"
                                f"Found: summary modifier '{summary2[0]}' in one dict "
                                f"AND status modifier '{status1[0]}' in another.\n"
                                f"These MUST be combined in ONE dict:\n"
                                f"  {{\n"
                                f"    \"name\": \"{name}\",\n"
                                f"    \"modifier\": [\"{summary2[0]}\", \"{status1[0]}\"]\n"
                                f"  }}\n"
                            )

    # Validate each attribute
    validated_attrs = []
    for attr in attributes:
        if is_field and "value" not in attr and "operator" not in attr:
            attr_name = attr.get("name")
            if attr_name is not None:
                if attr_name.endswith("_id") or attr_name in {"scientific_name", "taxon_rank"}:
                    continue
                if attr_name.endswith("_name") and search_index == "taxon":
                    continue
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
            if name.endswith("_name") and search_index == "taxon":
                other_names.append(name)
    validated_names.extend(other_names)
    return validated_names or None


def hash_dict(input_dict: dict) -> str:
    """Generate a short, consistent hash for a dictionary.

    Args:
        input_dict: Dictionary to hash

    Returns:
        A short hexadecimal hash string representing the input dictionary.
    """
    dict_str = json.dumps(input_dict, sort_keys=True)
    salted_str = SALT_FOR_HASHING + dict_str
    hash_obj = hashlib.sha256(salted_str.encode("utf-8"))
    # Return only the first 8 characters for shortness
    return hash_obj.hexdigest()[:8]


def validate_dict(input_dict: Any) -> bool:
    """Check if input is a valid non-empty dictionary.

    Args:
        input_dict: Input to check
    Returns:
        True if input is a valid dictionary, False otherwise.
    """
    if not isinstance(input_dict, dict) or not input_dict:
        return False
    hash_str = input_dict.pop("unique_id", None)
    if hash_str is None or not isinstance(hash_str, str) or len(hash_str) < 8:
        return False
    expected_hash = hash_dict(input_dict)
    return hash_str == expected_hash


async def set_search_index(
    taxa: list[str] | None,
    assemblies: list[str] | None,
    samples: list[str] | None,
    user_query: str
) -> None:
    """Set the search index for validation purposes.

    Args:
        taxa: List of taxon names or IDs
        assemblies: List of assembly accessions
        samples: List of sample accessions
        user_query: The original user question
    """
    search_index = None

    if assemblies:
        search_index = "assembly"
    elif samples:
        search_index = "sample"
    elif taxa:
        search_index = "taxon"
    else:
        # Try to infer from query
        from ..utilities import choose_search_index
        search_index = await choose_search_index(user_query)
        logger.info(f"Inferred search_index from query: {search_index}")
    return search_index
