"""Common utilities for processor tools.

This module provides shared functionality for process_* tools like
process_identifiers, process_attributes, and process_axes.
"""

from typing import Any

from ...logging_config import get_logger
from ..artifact_store import store
from .validation import hash_dict

logger = get_logger(__name__)


def finalise_and_store(data: dict[str, Any]) -> dict[str, str]:
    """Finalise processor output by hashing, adding unique_id, and storing.

    This common pattern is used by all process_* tools:
    1. Hash the data dictionary to create a unique identifier
    2. Add the hash as 'unique_id' to the data
    3. Store the data in the artifact store
    4. Return the artifact token

    Args:
        data: Dictionary containing processed parameters

    Returns:
        Dictionary with single key 'artifact_id' containing the artifact token
    """
    dict_hash = hash_dict(data)
    data["unique_id"] = dict_hash

    # Store canonical result and return an artifact token
    token = store(data)
    return {"artifact_id": token}
