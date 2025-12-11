"""Helper functions and utilities for GoaT MCP server tools.

This module re-exports all utilities from submodules for backward compatibility.
Individual submodules can be imported directly for more focused imports.
"""

# Re-export API utilities
from .api import make_goat_request

# Re-export constants
from .constants import GOAT_API_BASE, GOAT_DESCRIPTION, USER_AGENT

# Re-export formatting functions
from .formatting import (
    format_attribute_value,
    format_count,
    format_histogram_report,
    format_lineage,
    format_record,
    format_result_table,
    format_sources_report,
    rank_description,
)

# Re-export query building functions
from .query import (
    build_query_string,
    format_attributes,
    set_exclusions,
    set_search_tips,
)

# Re-export URL utilities
from .urls import update_query_string

# Re-export validation functions
from .validation import (
    validate_attribute,
    validate_attribute_name,
    validate_attribute_names,
    validate_attribute_value,
    validate_attributes,
    validate_operator,
)

__all__ = [
    # API utilities
    "make_goat_request",
    # Constants
    "GOAT_API_BASE",
    "GOAT_DESCRIPTION",
    "USER_AGENT",
    # Formatting
    "rank_description",
    "format_count",
    "format_lineage",
    "format_attribute_value",
    "format_record",
    "format_result_table",
    "format_sources_report",
    "format_histogram_report",
    # Query building
    "build_query_string",
    "format_attributes",
    "set_exclusions",
    "set_search_tips",
    # URL utilities
    "update_query_string",
    # Validation
    "validate_operator",
    "validate_attribute_value",
    "validate_attribute_name",
    "validate_attribute",
    "validate_attributes",
    "validate_attribute_names",
]
