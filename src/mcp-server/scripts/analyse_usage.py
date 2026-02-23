#!/usr/bin/env python3
"""Analyse MCP server usage patterns."""


import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import DATASTORE_NAME

LOG_FILE = Path.home() / ".goat-nlp" / "logs" / f"{DATASTORE_NAME}-usage.jsonl"


def reconstruct_chain(trace_id: str):
    """Show all tool calls in a single reasoning chain."""
    chain = []

    with open(LOG_FILE) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("trace_id") == trace_id:
                chain.append({
                    "tool": entry["tool"],
                    "params": entry["params"],
                    "success": entry["success"],
                    "duration_ms": entry["duration_ms"],
                    "timestamp": entry["timestamp"]
                })

    print(f"\n=== Trace {trace_id} ===")
    for i, call in enumerate(chain, 1):
        status = "✓" if call["success"] else "✗"
        print(f"\n{i}. {status} {call['tool']} ({call['duration_ms']:.0f}ms)")
        print(f"   Params: {call['params']}")


def find_error_chains():
    """Find all traces that had errors."""
    traces_with_errors = set()

    with open(LOG_FILE) as f:
        for line in f:
            entry = json.loads(line)
            if not entry["success"]:
                traces_with_errors.add(entry["trace_id"])

    print(f"Found {len(traces_with_errors)} chains with errors")
    for tid in list(traces_with_errors)[:5]:
        reconstruct_chain(tid)


def analyse_usage(days=7):
    """Analyse usage patterns from logs."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    tool_counts = Counter()
    tool_errors = Counter()
    tool_durations = defaultdict(list)
    param_patterns = defaultdict(Counter)

    with open(LOG_FILE) as f:
        for line in f:
            entry = json.loads(line)
            timestamp = datetime.fromisoformat(entry["timestamp"])

            if timestamp < cutoff:
                continue

            tool = entry["tool"]
            tool_counts[tool] += 1

            if not entry["success"]:
                tool_errors[tool] += 1

            if entry.get("duration_ms"):
                tool_durations[tool].append(entry["duration_ms"])

            # Track parameter patterns
            for key, value in entry["params"].items():
                param_patterns[f"{tool}.{key}"][str(value)] += 1

    print(f"\n=== Usage Analysis (last {days} days) ===\n")

    print("Most used tools:")
    for tool, count in tool_counts.most_common(10):
        error_rate = (tool_errors[tool] / count * 100) if count else 0
        avg_duration = sum(tool_durations[tool]) / len(tool_durations[tool]) if tool_durations[tool] else 0
        print(f"  {tool}: {count} calls, {error_rate:.1f}% errors, {avg_duration:.0f}ms avg")

    print("\nCommon parameter patterns:")
    for param, values in list(param_patterns.items())[:10]:
        top_value = values.most_common(1)[0]
        print(f"  {param}: '{top_value[0]}' ({top_value[1]} times)")

    print("\nPotential workflow patterns:")
    # Add sequence analysis here


if __name__ == "__main__":
    analyse_usage()
    find_error_chains()
