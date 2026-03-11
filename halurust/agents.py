"""All LLM-based agents for the HaluRust v2 pipeline."""

from __future__ import annotations

import json
import re

from .llm_client import LLMClient
from .models import (
    FixPlan,
    MiriReport,
    ReflectionResult,
    RepairContext,
    FixAttempt,
)
from .prompts import (
    COMPILE_FIX_SYSTEM,
    COMPILE_FIX_USER,
    FIX_AGENT_SYSTEM,
    FIX_AGENT_USER,
    FIX_EXPLANATION_SYSTEM,
    FIX_EXPLANATION_USER,
    HALLUCINATION_SYSTEM,
    HALLUCINATION_USER,
    PLAN_AGENT_SYSTEM,
    PLAN_AGENT_USER,
    REFLECTION_SYSTEM,
    REFLECTION_USER,
    REGRESSION_TEST_SYSTEM,
    REGRESSION_TEST_USER,
    SEMANTIC_CHECK_SYSTEM,
    SEMANTIC_CHECK_USER,
    TEST_GENERATE_SYSTEM,
    TEST_GENERATE_USER,
    build_few_shot_section,
    build_hallucinated_section,
    build_history_section,
    build_knowledge_section,
    build_localization_section,
    build_reflection_section,
)
from .rag import UBExample


# ====================================================================
# Plan Agent (enhanced with localization, knowledge graph, reflection)
# ====================================================================

class PlanAgent:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    def generate_plan(self, ctx: RepairContext) -> FixPlan:
        """Generate a fix plan from the full repair context."""
        user_msg = PLAN_AGENT_USER.format(
            source_code=ctx.source_code,
            error_report=ctx.miri_report.raw_stderr,
            ast_summary=ctx.ast_summary,
            localization_section=build_localization_section(ctx.localized_error),
            knowledge_section=build_knowledge_section(ctx.ub_type_knowledge),
            few_shot_section=build_few_shot_section(ctx.few_shot_examples),
            hallucinated_section=build_hallucinated_section(ctx.hallucinated_code or None),
            reflection_section=build_reflection_section(ctx.reflection),
        )
        raw = self._llm.chat(PLAN_AGENT_SYSTEM, user_msg)
        return _parse_plan(raw)

    def generate_plan_simple(
        self,
        source_code: str,
        miri_report: MiriReport,
        few_shots: list[UBExample] | None = None,
        hallucinated_code: str | None = None,
    ) -> FixPlan:
        """Backward-compatible simple plan generation."""
        from .ast_parser import ast_summary
        user_msg = PLAN_AGENT_USER.format(
            source_code=source_code,
            error_report=miri_report.raw_stderr,
            ast_summary=ast_summary(source_code),
            localization_section="",
            knowledge_section="",
            few_shot_section=build_few_shot_section(few_shots or []),
            hallucinated_section=build_hallucinated_section(hallucinated_code),
            reflection_section="",
        )
        raw = self._llm.chat(PLAN_AGENT_SYSTEM, user_msg)
        return _parse_plan(raw)


# ====================================================================
# Fix Agent (enhanced with multi-candidate generation)
# ====================================================================

class FixAgent:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    def generate_fix(
        self,
        source_code: str,
        miri_report: MiriReport,
        plan: FixPlan,
        previous_attempts: list[FixAttempt] | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a single fix candidate."""
        user_msg = FIX_AGENT_USER.format(
            source_code=source_code,
            error_report=miri_report.raw_stderr,
            fix_plan=plan.raw,
            history_section=build_history_section(previous_attempts or []),
        )
        raw = self._llm.chat(FIX_AGENT_SYSTEM, user_msg, temperature=temperature)
        return _extract_rust_code(raw)

    def generate_multiple(
        self,
        source_code: str,
        miri_report: MiriReport,
        plan: FixPlan,
        previous_attempts: list[FixAttempt] | None = None,
        temperatures: list[float] | None = None,
    ) -> list[str]:
        """Generate N fix candidates at different temperatures."""
        temps = temperatures or [0.2, 0.5, 0.8]
        candidates = []
        for t in temps:
            code = self.generate_fix(
                source_code, miri_report, plan, previous_attempts, temperature=t
            )
            candidates.append(code)
        return candidates

    def fix_compile_error(self, code: str, compile_errors: str) -> str:
        """Fix compilation errors in a candidate (inner loop)."""
        user_msg = COMPILE_FIX_USER.format(code=code, compile_errors=compile_errors)
        raw = self._llm.chat(COMPILE_FIX_SYSTEM, user_msg)
        return _extract_rust_code(raw)


# ====================================================================
# Hallucination Agent (kept from v1)
# ====================================================================

class HallucinationAgent:
    """Generates a quick (potentially flawed) fix for use as reference."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def generate(self, source_code: str, miri_report: MiriReport) -> str:
        user_msg = HALLUCINATION_USER.format(
            source_code=source_code,
            error_report=miri_report.raw_stderr,
        )
        raw = self._llm.chat(HALLUCINATION_SYSTEM, user_msg, temperature=0.7)
        return _extract_rust_code(raw)


# ====================================================================
# Reflection Agent (new)
# ====================================================================

class ReflectionAgent:
    """Analyzes why a fix attempt failed and suggests adjustments."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def reflect(
        self,
        original_code: str,
        attempted_code: str,
        plan: FixPlan,
        miri_result: MiriReport,
        fix_status: str,
        previous_reflections: list[ReflectionResult] | None = None,
    ) -> ReflectionResult:
        prev_text = ""
        if previous_reflections:
            parts = ["## Previous Reflections"]
            for i, r in enumerate(previous_reflections, 1):
                parts.append(f"\n### Reflection {i}")
                parts.append(f"Failure: {r.failure_analysis}")
                parts.append(f"Suggestion: {r.next_step_suggestion}")
            prev_text = "\n".join(parts)

        user_msg = REFLECTION_USER.format(
            original_code=original_code,
            fix_plan=plan.raw,
            attempted_code=attempted_code,
            miri_result=miri_result.raw_stderr,
            fix_status=fix_status,
            previous_reflections=prev_text,
        )
        raw = self._llm.chat(REFLECTION_SYSTEM, user_msg)
        return _parse_reflection(raw)


# ====================================================================
# Semantic Preservation Checker (new)
# ====================================================================

class SemanticPreservationChecker:
    """LLM-based check: does the fix preserve original program semantics?"""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def check(self, original_code: str, fixed_code: str, error_type: str) -> float:
        """Return a 0~1 score for semantic preservation."""
        user_msg = SEMANTIC_CHECK_USER.format(
            original_code=original_code,
            fixed_code=fixed_code,
            error_type=error_type,
        )
        raw = self._llm.chat(SEMANTIC_CHECK_SYSTEM, user_msg, temperature=0.1)
        return _parse_semantic_score(raw)


# ====================================================================
# Test Generate Agent (new)
# ====================================================================

class TestGenerateAgent:
    """Generates test cases that exercise the code's memory safety."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def generate_tests(self, source_code: str) -> str:
        user_msg = TEST_GENERATE_USER.format(source_code=source_code)
        raw = self._llm.chat(TEST_GENERATE_SYSTEM, user_msg)
        return _extract_rust_code(raw)


# ====================================================================
# Fix Explanation Generator (new — post-fix)
# ====================================================================

class FixExplanationGenerator:
    """Generates a human-readable explanation of a successful fix."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def explain(
        self,
        original_code: str,
        fixed_code: str,
        error_type: str,
        error_message: str,
    ) -> str:
        user_msg = FIX_EXPLANATION_USER.format(
            original_code=original_code,
            fixed_code=fixed_code,
            error_type=error_type,
            error_message=error_message,
        )
        return self._llm.chat(FIX_EXPLANATION_SYSTEM, user_msg, temperature=0.2)


# ====================================================================
# Regression Test Generator (new — post-fix)
# ====================================================================

class RegressionTestGenerator:
    """Generates regression tests after a successful fix."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def generate(
        self,
        original_code: str,
        fixed_code: str,
        error_type: str,
        explanation: str,
    ) -> str:
        user_msg = REGRESSION_TEST_USER.format(
            original_code=original_code,
            fixed_code=fixed_code,
            error_type=error_type,
            explanation=explanation,
        )
        raw = self._llm.chat(REGRESSION_TEST_SYSTEM, user_msg)
        return _extract_rust_code(raw)


# ====================================================================
# Parsing helpers
# ====================================================================

def _parse_plan(raw: str) -> FixPlan:
    plan = FixPlan(raw=raw)
    sections = re.split(r"^## ", raw, flags=re.MULTILINE)
    for section in sections:
        lower = section.lower()
        content = section.split("\n", 1)[1].strip() if "\n" in section else ""
        if lower.startswith("analysis"):
            plan.analysis = content
        elif lower.startswith("root cause"):
            plan.root_cause = content
        elif lower.startswith("fix strategy") or lower.startswith("strategy"):
            plan.strategy = content
        elif lower.startswith("steps"):
            plan.steps = [
                line.strip().lstrip("0123456789.").strip()
                for line in content.splitlines()
                if line.strip() and line.strip()[0].isdigit()
            ]
    return plan


def _extract_rust_code(raw: str) -> str:
    pattern = r"```rust\s*\n(.*?)```"
    match = re.search(pattern, raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    pattern2 = r"```\s*\n(.*?)```"
    match2 = re.search(pattern2, raw, re.DOTALL)
    if match2:
        return match2.group(1).strip()
    return raw.strip()


def _parse_reflection(raw: str) -> ReflectionResult:
    result = ReflectionResult(raw=raw)
    sections = re.split(r"^## ", raw, flags=re.MULTILINE)
    for section in sections:
        lower = section.lower()
        content = section.split("\n", 1)[1].strip() if "\n" in section else ""
        if lower.startswith("failure analysis"):
            result.failure_analysis = content
        elif lower.startswith("ineffective strateg"):
            result.ineffective_strategies = [
                line.strip().lstrip("-•* ").strip()
                for line in content.splitlines()
                if line.strip() and line.strip()[0] in "-•*"
            ]
        elif lower.startswith("next step"):
            result.next_step_suggestion = content
    return result


def _parse_semantic_score(raw: str) -> float:
    """Parse the JSON response from semantic checker, fallback to 0.5."""
    try:
        # Try direct JSON parse
        data = json.loads(raw)
        return float(data.get("score", 0.5))
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: look for score in text
    m = re.search(r'"score"\s*:\s*([\d.]+)', raw)
    if m:
        return min(1.0, max(0.0, float(m.group(1))))
    return 0.5
