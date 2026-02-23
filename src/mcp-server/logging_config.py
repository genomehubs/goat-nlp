"""Shared logging configuration for GenomeHubs MCP server."""

import json
import logging
import sys
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DATASTORE_NAME

# Create logs directory
LOG_DIR = Path.home() / ".goat-nlp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log files
GENERAL_LOG = LOG_DIR / f"{DATASTORE_NAME}-mcp.log"
USAGE_LOG = LOG_DIR / f"{DATASTORE_NAME}-usage.jsonl"  # JSON Lines for analysis
ERROR_LOG = LOG_DIR / f"{DATASTORE_NAME}-errors.log"

# Thread-safe context var for the current trace
_trace_id_var: ContextVar[str] = ContextVar('trace_id', default=None)


def set_trace_id(tid: str):
    """Set the correlation ID for this request chain."""
    _trace_id_var.set(tid)


def get_trace_id() -> str:
    """Get current trace ID."""
    tid = _trace_id_var.get()
    if tid is None:
        tid = str(uuid.uuid4())
        _trace_id_var.set(tid)
    return tid


class UsageLogger:
    """Structured logger for tracking tool usage patterns."""

    def __init__(self):
        self.usage_log = USAGE_LOG

    def log_tool_call(
        self,
        tool_name: str,
        params: dict[str, Any],
        duration_ms: float | None = None,
        success: bool = True,
        error: str | None = None,
        result_summary: dict[str, Any] | None = None,
        error_details: dict[str, Any] | None = None,
    ):
        """Log a tool invocation with structured data.

        Args:
            tool_name: Name of the tool called
            params: Parameters passed to the tool
            duration_ms: Execution time in milliseconds
            success: Whether the call succeeded
            error: Error message if failed
            result_summary: Summary stats about the result (count, fields, etc.)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": get_trace_id(),
            "tool": tool_name,
            "params": self._sanitize_params(params),
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
            "error_details": error_details or {},
            "result_summary": result_summary or {}
        }

        with open(self.usage_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _sanitize_params(self, params: dict) -> dict:
        """Remove sensitive data from params before logging."""
        # Copy and sanitize
        sanitized = params.copy()
        # Could filter auth tokens, personal data, etc. if needed
        return sanitized


general_handler = logging.FileHandler(GENERAL_LOG)
general_handler.setLevel(logging.INFO)

error_handler = logging.FileHandler(ERROR_LOG)
error_handler.setLevel(logging.ERROR)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[general_handler, error_handler, stdout_handler],
)


# Global usage logger instance
usage_logger = UsageLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__ from the calling module

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_tool_usage(
    tool_name: str,
    params: dict[str, Any],
    duration_ms: float | None = None,
    success: bool = True,
    error: str | None = None,
    result_summary: dict[str, Any] | None = None,
    exc: BaseException | None = None,
):
    """Convenience function for logging tool usage.

    Args:
        tool_name: Name of the tool called
        params: Parameters passed to the tool
        duration_ms: Execution time in milliseconds
        success: Whether the call succeeded
        error: Error message if failed
        result_summary: Summary stats about the result
    """
    error_details: dict[str, Any] = {}

    # If an explicit exception isn't provided, use active exception in the current except block.
    # This keeps existing call sites working while still capturing line number details.
    active_exc = exc if exc is not None else sys.exc_info()[1]

    if active_exc is not None and hasattr(active_exc, "__traceback__"):
        tb = active_exc.__traceback__
        if tb is not None:
            frames = traceback.extract_tb(tb)
            if frames:
                last = frames[-1]
                error_details = {
                    "type": type(active_exc).__name__,
                    "file": last.filename,
                    "line": last.lineno,
                    "function": last.name,
                }

    usage_logger.log_tool_call(
        tool_name=tool_name,
        params=params,
        duration_ms=duration_ms,
        success=success,
        error=error,
        result_summary=result_summary,
        error_details=error_details,
    )
