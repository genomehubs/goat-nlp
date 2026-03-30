"""Shared logging configuration for GenomeHubs MCP server."""

import glob
import gzip
import json
import logging
import logging.handlers
import os
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
GENERAL_LOG = LOG_DIR / f"{DATASTORE_NAME.lower()}-mcp.log"
USAGE_LOG = LOG_DIR / f"{DATASTORE_NAME.lower()}-usage.jsonl"  # JSON Lines for analysis
ERROR_LOG = LOG_DIR / f"{DATASTORE_NAME.lower()}-errors.log"

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


class GzipTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """TimedRotatingFileHandler that gzips rotated log files for disk savings.

    After rollover, any rotated files that are not already gzipped are compressed
    with gzip and the original is removed.
    """

    def doRollover(self):
        super().doRollover()
        # Compress any rotated files for this base filename
        pattern = f"{self.baseFilename}.*"
        for fname in glob.glob(pattern):
            if fname.endswith(".gz"):
                continue
            # Skip the current active log file
            if os.path.abspath(fname) == os.path.abspath(self.baseFilename):
                continue
            try:
                with (open(fname, "rb") as f_in, gzip.open(f"{fname}.gz", "wb") as f_out):
                    f_out.writelines(f_in)
                os.remove(fname)
            except Exception:
                # Fail silently - logging shouldn't crash the app
                logging.getLogger(__name__).exception("Failed to compress rotated log %s", fname)


class UsageLogger:
    """Structured logger for tracking tool usage patterns using a rotating file handler."""

    def __init__(self):
        # Use a dedicated logger for usage entries so rotation can be applied separately
        self.logger = logging.getLogger("goat.usage")
        # If no handlers configured for this logger, add one
        if not any(isinstance(h, (logging.handlers.TimedRotatingFileHandler, GzipTimedRotatingFileHandler))
                   for h in self.logger.handlers):
            handler = GzipTimedRotatingFileHandler(str(USAGE_LOG), when="midnight", backupCount=30, utc=False)
            handler.suffix = "%Y-%m-%d"
            handler.setLevel(logging.INFO)
            # The logger will write raw JSON lines, so use a simple message formatter
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
            self.logger.propagate = False

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
        """Log a tool invocation with structured JSON data (one JSON object per line).

        This writes a single JSON object per line to the usage log via the dedicated
        usage logger, which handles rotation and compression.
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
        # Write JSON line via logger so it benefits from rotation/compression
        try:
            self.logger.info(json.dumps(entry, default=str))
        except Exception:
            # Last-resort fallback to append (avoid losing logs)
            try:
                with open(USAGE_LOG, "a") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
            except Exception:
                logging.getLogger(__name__).exception("Failed to write usage log entry")

    def _sanitize_params(self, params: dict) -> dict:
        """Remove sensitive data from params before logging."""
        return params.copy()


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
            if frames := traceback.extract_tb(tb):
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
