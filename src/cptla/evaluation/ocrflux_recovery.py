"""Bounded operational recovery, without changing the frozen inference protocol."""

import re


def initialization_retry_allowed(summary, raw_count):
    return (
        summary.get("status") == "failed"
        and summary.get("pages") == 0
        and summary.get("documents") == []
        and raw_count == 0
        and summary.get("error", "").startswith(
            "AssertionError: Error in memory profiling. Initial used memory "
        )
    )


def recovery_next(state, document):
    if not re.fullmatch(r"PMC[0-9]+", document):
        raise ValueError("Invalid recovery document")
    if state.get(document, 0) >= 3 or sum(state.values()) >= 20:
        raise RuntimeError("Initialization recovery limit reached")
    return {**state, document: state.get(document, 0) + 1}
