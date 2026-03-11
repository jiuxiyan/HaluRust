"""Error Localization — combine Miri error line numbers with AST to pinpoint UB."""

from __future__ import annotations

import re

from .ast_parser import (
    extract_unsafe_blocks,
    get_function_nodes,
    ASTNode,
)
from .models import LocalizedError, MiriReport


def localize_error(source_code: str, miri_report: MiriReport) -> LocalizedError:
    """Pinpoint the error location by matching Miri line numbers to AST functions."""
    error_line = _extract_line_number(miri_report)
    if error_line == 0:
        return LocalizedError(error_line=0, code_snippet=source_code)

    functions = get_function_nodes(source_code)
    source_lines = source_code.splitlines()

    # Find the enclosing function
    enclosing_fn: ASTNode | None = None
    for fn in functions:
        if fn.start_line <= error_line <= fn.end_line:
            enclosing_fn = fn
            break

    # Check if error is inside an unsafe block
    unsafe_context = False
    for ub in extract_unsafe_blocks(source_code):
        if ub.start_line <= error_line <= ub.end_line:
            unsafe_context = True
            break

    # Extract a code snippet around the error (±5 lines)
    start = max(0, error_line - 6)
    end = min(len(source_lines), error_line + 5)
    snippet_lines = []
    for i in range(start, end):
        marker = " >> " if (i + 1) == error_line else "    "
        snippet_lines.append(f"{marker}L{i + 1}: {source_lines[i]}")
    snippet = "\n".join(snippet_lines)

    fn_name = ""
    fn_range = (0, 0)
    if enclosing_fn:
        fn_name = _extract_fn_name(enclosing_fn)
        fn_range = (enclosing_fn.start_line, enclosing_fn.end_line)

    related_vars = _extract_related_variables(miri_report)

    return LocalizedError(
        error_line=error_line,
        function_name=fn_name,
        function_range=fn_range,
        code_snippet=snippet,
        unsafe_context=unsafe_context,
        related_variables=related_vars,
    )


def _extract_line_number(report: MiriReport) -> int:
    """Extract the primary error line number from Miri stderr."""
    # Pattern: --> src/main.rs:12:5  or  --> src/lib.rs:42:10
    for line in report.raw_stderr.splitlines():
        m = re.search(r"-->\s+\S+:(\d+):\d+", line)
        if m:
            return int(m.group(1))
    # Fallback: look for "at line N" style
    for line in report.raw_stderr.splitlines():
        m = re.search(r"at.*?:(\d+):\d+", line)
        if m:
            return int(m.group(1))
    return 0


def _extract_fn_name(fn_node: ASTNode) -> str:
    """Extract function name from a function_item AST node."""
    for child in fn_node.children:
        if child.type == "identifier":
            return child.text
    first_line = fn_node.text.split("\n")[0]
    m = re.search(r"fn\s+(\w+)", first_line)
    return m.group(1) if m else first_line[:60]


def _extract_related_variables(report: MiriReport) -> list[str]:
    """Extract variable/pointer names mentioned in the Miri report."""
    variables: list[str] = []
    text = report.raw_stderr

    # Miri often mentions: "tag <TAG> for <variable>"
    for m in re.finditer(r"tag \S+ (?:created|for) .*?`(\w+)`", text):
        if m.group(1) not in variables:
            variables.append(m.group(1))

    # References to identifiers in backticks
    for m in re.finditer(r"`(\w+)`", text):
        name = m.group(1)
        if name not in variables and not name[0].isupper() and name not in ("main", "test", "fn"):
            variables.append(name)

    return variables[:10]


def build_localization_text(loc: LocalizedError) -> str:
    """Build a text block for LLM context."""
    lines = ["## Error Localization"]
    if loc.function_name:
        lines.append(f"Function: `{loc.function_name}` (lines {loc.function_range[0]}-{loc.function_range[1]})")
    if loc.error_line:
        lines.append(f"Error at line: {loc.error_line}")
    lines.append(f"In unsafe context: {'Yes' if loc.unsafe_context else 'No'}")
    if loc.related_variables:
        lines.append(f"Related variables: {', '.join(loc.related_variables)}")
    if loc.code_snippet:
        lines.append(f"\nCode context:\n```\n{loc.code_snippet}\n```")
    return "\n".join(lines)
