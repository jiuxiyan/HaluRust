"""Prompt templates for all agents in the HaluRust v2 pipeline."""

from __future__ import annotations

# ====================================================================
# Plan Agent
# ====================================================================

PLAN_AGENT_SYSTEM = """\
You are a Rust memory safety expert. Your task is to analyze Rust code that triggers \
Undefined Behavior (UB) detected by Miri, and produce a detailed fix plan.

You will receive:
1. The original Rust source code
2. The Miri error report
3. An AST summary of the code
4. Error localization (pinpointed function and line)
5. UB type knowledge (common fix patterns for this UB type)
6. (Optional) Few-shot examples of similar UB fixes
7. (Optional) A hallucinated fix attempt for reference
8. (Optional) Reflection from previous failed attempts

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
- If reflection from a previous attempt is provided, avoid repeating strategies that already failed
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

{localization_section}

{knowledge_section}

{few_shot_section}

{hallucinated_section}

{reflection_section}

Please analyze the UB and produce a fix plan.
"""

# ====================================================================
# Fix Agent
# ====================================================================

FIX_AGENT_SYSTEM = """\
You are a Rust code repair agent. Given the original buggy code, the Miri error report, \
and a fix plan, you must produce the corrected Rust code.

Rules:
- Output ONLY the complete fixed Rust source code, wrapped in ```rust ... ```
- Include the complete file including the main() function
- Preserve the overall program structure and intent
- Make minimal changes to fix the UB while keeping the code meaningful
- The code must compile and pass Miri checks (no Undefined Behavior)
- Do NOT add explanations outside the code block
- Do NOT include miri test annotations (//~ ERROR, //@compile-flags, etc.)
- If the original uses unsafe code incorrectly, replace with safe alternatives where possible
- If unsafe is truly needed, ensure it is sound
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

# ====================================================================
# Fix Agent — compile error repair (inner loop)
# ====================================================================

COMPILE_FIX_SYSTEM = """\
You are a Rust compiler error fixer. The code below fails to compile. \
Fix ONLY the compilation errors while preserving the intended fix logic.

Output ONLY the complete fixed source code wrapped in ```rust ... ```.
"""

COMPILE_FIX_USER = """\
## Code (fails to compile)
```rust
{code}
```

## Compiler Errors
```
{compile_errors}
```

Fix the compilation errors and output the corrected code.
"""

# ====================================================================
# Hallucination Agent (kept from v1)
# ====================================================================

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

# ====================================================================
# Reflection Agent (new)
# ====================================================================

REFLECTION_SYSTEM = """\
You are a Rust debugging expert reviewing a failed UB fix attempt. \
Your job is to analyze why the fix did not work and provide actionable guidance \
for the next attempt.

Produce your analysis in this exact format:

## Failure Analysis
<Why did the fix fail? What UB remains or was introduced?>

## Ineffective Strategies
- <Strategy 1 that should NOT be retried>
- <Strategy 2 ...>

## Next Step Suggestion
<What specific approach should the next attempt take?>
"""

REFLECTION_USER = """\
## Original Code
```rust
{original_code}
```

## Fix Plan That Was Tried
{fix_plan}

## Attempted Fix
```rust
{attempted_code}
```

## Miri Result After Fix
```
{miri_result}
```

## Fix Status: {fix_status}

{previous_reflections}

Analyze why this fix failed and suggest what to try next.
"""

# ====================================================================
# Semantic Preservation Checker (new)
# ====================================================================

SEMANTIC_CHECK_SYSTEM = """\
You are a Rust code reviewer. Compare the original code and a proposed fix. \
Evaluate whether the fix preserves the original program's intended semantics \
(behavior, output, side effects).

Respond with ONLY a JSON object:
{
  "score": <float 0.0 to 1.0>,
  "preserved": <true/false>,
  "explanation": "<brief explanation>"
}

- 1.0 = semantics fully preserved
- 0.5 = minor behavioral changes but core logic intact
- 0.0 = semantics completely changed
"""

SEMANTIC_CHECK_USER = """\
## Original Code
```rust
{original_code}
```

## Fixed Code
```rust
{fixed_code}
```

## The fix was intended to resolve: {error_type}

Evaluate semantic preservation.
"""

# ====================================================================
# Test Generate Agent (new)
# ====================================================================

TEST_GENERATE_SYSTEM = """\
You are a Rust testing expert. Given Rust source code, generate test functions \
that exercise the code's functionality, especially edge cases around memory safety.

Rules:
- Output test functions wrapped in ```rust ... ```
- Use #[test] attribute for each test
- Include tests that would trigger UB if the code has memory safety issues
- Keep tests focused and minimal
"""

TEST_GENERATE_USER = """\
## Source Code
```rust
{source_code}
```

Generate test functions for this code.
"""

# ====================================================================
# Regression Test Generator (new — post-fix)
# ====================================================================

REGRESSION_TEST_SYSTEM = """\
You are a Rust testing expert. Given the original buggy code, the fix, and the \
UB type that was fixed, generate regression tests that verify:
1. The original functionality is preserved
2. The UB is truly eliminated
3. Edge cases are covered

Output test functions wrapped in ```rust ... ``` using #[test] attribute.
"""

REGRESSION_TEST_USER = """\
## Original Code (had UB)
```rust
{original_code}
```

## Fixed Code
```rust
{fixed_code}
```

## UB Type Fixed: {error_type}
## Fix Explanation: {explanation}

Generate regression tests.
"""

# ====================================================================
# Fix Explanation Generator (new — post-fix)
# ====================================================================

FIX_EXPLANATION_SYSTEM = """\
You are a Rust safety documentation expert. Given the original buggy code, \
the fixed code, and the UB type, write a clear explanation of:
1. What the original UB was
2. Why it occurred (root cause)
3. What the fix changed
4. Why the fix is correct

Keep the explanation concise (3-6 sentences). Output plain text only.
"""

FIX_EXPLANATION_USER = """\
## Original Code
```rust
{original_code}
```

## Fixed Code
```rust
{fixed_code}
```

## UB Type: {error_type}
## Miri Error: {error_message}

Write a clear explanation of this fix.
"""


# ====================================================================
# Section builders
# ====================================================================

def build_few_shot_section(examples: list) -> str:
    if not examples:
        return ""
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
        return ""
    return f"## Hallucinated Fix Reference\n```rust\n{hallucinated_code}\n```"


def build_history_section(history: list) -> str:
    if not history:
        return ""
    parts = ["## Previous Attempts (failed)"]
    for i, attempt in enumerate(history, 1):
        parts.append(f"\n### Attempt {i}")
        parts.append(f"Code:\n```rust\n{attempt.fixed_code}\n```")
        parts.append(f"Result: {attempt.miri_report.summary}")
        if hasattr(attempt, "score") and attempt.score:
            parts.append(f"Score: {attempt.score.summary}")
    return "\n".join(parts)


def build_reflection_section(reflection) -> str:
    if not reflection:
        return ""
    parts = ["## Reflection from Previous Attempt"]
    if reflection.failure_analysis:
        parts.append(f"**Failure Analysis:** {reflection.failure_analysis}")
    if reflection.ineffective_strategies:
        parts.append("**Avoid these strategies:**")
        for s in reflection.ineffective_strategies:
            parts.append(f"  - {s}")
    if reflection.next_step_suggestion:
        parts.append(f"**Suggested next approach:** {reflection.next_step_suggestion}")
    return "\n".join(parts)


def build_localization_section(localized_error) -> str:
    if not localized_error or not localized_error.error_line:
        return ""
    from .error_localization import build_localization_text
    return build_localization_text(localized_error)


def build_knowledge_section(knowledge_text: str) -> str:
    if not knowledge_text:
        return ""
    return knowledge_text
