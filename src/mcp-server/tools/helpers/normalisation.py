"""Normalisation utilities for processor tools.

This module provides common input normalisation functions used by
process_* tools to ensure consistent handling of inputs.
"""

from typing import Callable


def normalise_to_list(value: list[str] | str | None) -> list[str]:
    """Normalise input to a list of strings.

    Handles three cases:
    1. None -> empty list
    2. Single string -> list with one element
    3. Already a list -> return as-is

    Args:
        value: Input value that may be None, a string, or a list of strings

    Returns:
        A list of strings (may be empty)

    Examples:
        >>> normalise_to_list(None)
        []
        >>> normalise_to_list("Mammalia")
        ['Mammalia']
        >>> normalise_to_list(["Felis", "Canis"])
        ['Felis', 'Canis']
    """
    if value is None:
        return []
    elif isinstance(value, str):
        return [value]
    return value


def normalise_string_list(
    value: list[str] | str | None,
    strip: bool = True,
    remove_empty: bool = True,
    transform: Callable | None = None,
) -> list[str]:
    """Normalise input to a list of strings with optional transformations.

    Args:
        value: Input value that may be None, a string, or a list of strings
        strip: Whether to strip whitespace from each string
        remove_empty: Whether to remove empty strings after stripping
        transform: Optional function to apply to each string (e.g., str.lower)

    Returns:
        A normalised list of strings

    Examples:
        >>> normalise_string_list([" Felis ", "", "Canis"])
        ['Felis', 'Canis']
        >>> normalise_string_list("  Mammalia  ")
        ['Mammalia']
        >>> normalise_string_list(["Felis", "Canis"], transform=str.upper)
        ['FELIS', 'CANIS']
    """
    items = normalise_to_list(value)

    if strip:
        items = [item.strip() for item in items]

    if transform:
        items = [transform(item) for item in items]

    if remove_empty:
        items = [item for item in items if item != ""]

    return items
