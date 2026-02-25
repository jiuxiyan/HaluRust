"""Plan Agent and Fix Agent implementations."""

from __future__ import annotations

import re

from .ast_parser import ast_summary
from .llm_client import LLMClient
from .models import FixPlan, MiriReport
from .prompts import (
    FIX_AGENT_SYSTEM,
    FIX_AGENT_USER,
    HALLUCINATION_SYSTEM,
    HALLUCINATION_USER,
    PLAN_AGENT_SYSTEM,
    PLAN_AGENT_USER,
    build_few_shot_section,
    build_hallucinated_section,
    build_history_section,
)
from .rag import UBExample


class PlanAgent:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    def generate_plan(
        self,
        source_code: str,
        miri_report: MiriReport,
        few_shots: list[UBExample] | None = None,
        hallucinated_code: str | None = None,
    ) -> FixPlan:
        ast_text = ast_summary(source_code)

        user_msg = PLAN_AGENT_USER.format(
            source_code=source_code,
            error_report=miri_report.raw_stderr,
            ast_summary=ast_text,
            few_shot_section=build_few_shot_section(few_shots or []),
            hallucinated_section=build_hallucinated_section(hallucinated_code),
        )

        raw = self._llm.chat(PLAN_AGENT_SYSTEM, user_msg)
        return _parse_plan(raw)


class FixAgent:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    def generate_fix(
        self,
        source_code: str,
        miri_report: MiriReport,
        plan: FixPlan,
        previous_attempts: list | None = None,
    ) -> str:
        user_msg = FIX_AGENT_USER.format(
            source_code=source_code,
            error_report=miri_report.raw_stderr,
            fix_plan=plan.raw,
            history_section=build_history_section(previous_attempts or []),
        )

        raw = self._llm.chat(FIX_AGENT_SYSTEM, user_msg)
        return _extract_rust_code(raw)


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
