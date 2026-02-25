"""Prompt templates for Plan Agent and Fix Agent."""

from __future__ import annotations

PLAN_AGENT_SYSTEM = """\
You are a Rust memory safety expert. Your task is to analyze Rust code that triggers \
Undefined Behavior (UB) detected by Miri, and produce a detailed fix plan.

You will receive:
1. The original Rust source code
2. The Miri error report
3. An AST summary of the code
4. (Optional) Few-shot examples of similar UB fixes
5. (Optional) A hallucinated fix attempt for reference

Produce a structured fix plan in the following format:

## Analysis
<What the code does and where the UB occurs>

## Root Cause
<The fundamental reason for the UB>

## Fix Strategy
<High-level approach to fix the UB while preserving functionality>

## Steps
1. <Concrete step 1>
2. <Concrete step 2>
...

Important guidelines:
- Preserve the original function signatures and public API when possible
- Prefer safe Rust idioms over raw pointer manipulation
- If unsafe is necessary, explain why and how it is sound
- Consider ownership, borrowing, and lifetime rules carefully
"""

PLAN_AGENT_USER = """\
## Source Code
```rust
{source_code}
```

## Miri Error Report
```
{error_report}
```

## AST Summary
```
{ast_summary}
```

{few_shot_section}

{hallucinated_section}

Please analyze the UB and produce a fix plan.
"""

FIX_AGENT_SYSTEM = """\
You are a Rust code repair agent. Given the original buggy code, the Miri error report, \
and a fix plan, you must produce the corrected Rust code.

Rules:
- Output ONLY the complete fixed Rust source code, wrapped in ```rust ... ```
- Do NOT include the test code — only the library/source code
- Preserve function signatures and the public API
- Make minimal changes to fix the UB
- The code must compile and pass Miri checks
- Do NOT add explanations outside the code block
"""

FIX_AGENT_USER = """\
## Original Code
```rust
{source_code}
```

## Miri Error Report
```
{error_report}
```

## Fix Plan
{fix_plan}

{history_section}

Please produce the fixed Rust code.
"""

HALLUCINATION_SYSTEM = """\
You are a Rust developer who is somewhat familiar with unsafe Rust. Given buggy code \
and a Miri error report, produce a quick fix attempt. Your fix may not be perfect — \
that's okay. Focus on addressing the reported UB type.

Output ONLY the complete fixed source code wrapped in ```rust ... ```.
"""

HALLUCINATION_USER = """\
## Buggy Code
```rust
{source_code}
```

## Miri Error
```
{error_report}
```

Produce a quick fix.
"""


def build_few_shot_section(examples: list) -> str:
    if not examples:
        return "## Few-shot Examples\n(No examples available)"
    parts = ["## Few-shot Examples"]
    for i, ex in enumerate(examples, 1):
        parts.append(f"\n### Example {i} ({ex.error_type})")
        parts.append(f"Buggy:\n```rust\n{ex.buggy_code}\n```")
        parts.append(f"Error:\n```\n{ex.error_report}\n```")
        parts.append(f"Fixed:\n```rust\n{ex.fixed_code}\n```")
        if ex.explanation:
            parts.append(f"Explanation: {ex.explanation}")
    return "\n".join(parts)


def build_hallucinated_section(hallucinated_code: str | None) -> str:
    if not hallucinated_code:
        return "## Hallucinated Fix Reference\n(Not available)"
    return f"## Hallucinated Fix Reference\n```rust\n{hallucinated_code}\n```"


def build_history_section(history: list) -> str:
    if not history:
        return ""
    parts = ["## Previous Attempts (failed)"]
    for i, attempt in enumerate(history, 1):
        parts.append(f"\n### Attempt {i}")
        parts.append(f"Code:\n```rust\n{attempt.fixed_code}\n```")
        parts.append(f"Result: {attempt.miri_report.summary}")
    return "\n".join(parts)
