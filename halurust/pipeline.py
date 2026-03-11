"""Main pipeline: orchestrates the three-layer iterative fix loop.

Outer loop  — handles multiple UBs sequentially (UB Prioritizer)
Main loop   — Plan → Fix (N candidates) → Critic → decision  (max_iterations)
Inner loop  — cargo check → compile-error fix → re-check     (compile_fix_retries)
"""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .agents import (
    FixAgent,
    HallucinationAgent,
    PlanAgent,
    ReflectionAgent,
    TestGenerateAgent,
)
from .compile_checker import CompileChecker
from .config import HaluRustConfig
from .context_assembler import ContextAssembler
from .critic import MultiDimensionalCritic
from .experience import ExperienceAccumulator
from .llm_client import LLMClient
from .miri_runner import parse_miri_flags, run_miri, run_miri_single_file
from .models import (
    CriticScore,
    FixAttempt,
    FixCandidate,
    FixHistory,
    FixStatus,
    ReflectionResult,
)
from .rag import UBExampleLibrary

console = Console()

_DEFAULT_LIBRARY_PATH = str(Path(__file__).parent.parent / "ub_example_library")


class HaluRustPipeline:
    """HaluRust v2 pipeline with three-layer loop architecture."""

    def __init__(
        self,
        config: HaluRustConfig,
        mock: bool = False,
        library_path: str | None = None,
    ):
        self._config = config

        # LLM client
        if mock:
            from .mock_llm import MockLLMClient
            llm = MockLLMClient(config)  # type: ignore[arg-type]
        else:
            llm = LLMClient(config)
        self._llm = llm

        # Agents
        self._plan_agent = PlanAgent(llm)
        self._fix_agent = FixAgent(llm)
        self._hallucination_agent = HallucinationAgent(llm)
        self._reflection_agent = ReflectionAgent(llm) if config.enable_reflection else None
        self._test_gen_agent = TestGenerateAgent(llm) if config.enable_test_generation else None

        # Tools
        self._compile_checker = CompileChecker(config)
        self._critic = MultiDimensionalCritic(config, llm)

        # RAG library
        lib_path = library_path or _DEFAULT_LIBRARY_PATH
        if Path(lib_path).exists():
            self._rag = UBExampleLibrary(lib_path)
            if self._rag.size > 0:
                console.print(f"[dim]RAG library loaded: {self._rag.size} examples[/dim]")
        else:
            self._rag = UBExampleLibrary()
        self._library_path = lib_path

        # Context assembler
        self._ctx_assembler = ContextAssembler(self._rag)

        # Experience accumulator
        self._experience = (
            ExperienceAccumulator(config, llm, self._rag, lib_path)
            if config.enable_experience_accumulation
            else None
        )

    # ===================================================================
    # Public API: lib + test mode
    # ===================================================================

    def run(self, source_code: str, test_code: str) -> FixHistory:
        console.print(Panel("[bold]HaluRust v2 Pipeline[/bold]", style="cyan"))

        # ----- Phase A: Detection -----
        console.print("\n[bold yellow]Phase A:[/bold yellow] Running Miri on original code...")
        original_report = run_miri(source_code, test_code, self._config)
        console.print(f"  Result: {original_report.summary}")

        if original_report.passed:
            console.print("[green]No UB detected — nothing to fix![/green]")
            return FixHistory(
                source_file="<inline>", test_file="<inline>",
                original_code=source_code, original_report=original_report,
            )

        history = FixHistory(
            source_file="<inline>", test_file="<inline>",
            original_code=source_code, original_report=original_report,
        )

        # ----- Phase B: Context Construction -----
        console.print("\n[bold yellow]Phase B:[/bold yellow] Building repair context...")

        hallucinated = ""
        if self._config.enable_hallucination:
            console.print("  [dim]Generating hallucinated fix reference...[/dim]")
            hallucinated = self._hallucination_agent.generate(source_code, original_report)

        ctx = self._ctx_assembler.assemble(
            source_code=source_code,
            test_code=test_code,
            miri_report=original_report,
            hallucinated_code=hallucinated,
        )

        if ctx.few_shot_examples:
            console.print(f"  Retrieved {len(ctx.few_shot_examples)} few-shot examples")
        console.print(f"  Error localized to: {ctx.localized_error.function_name or 'unknown'} (L{ctx.localized_error.error_line})")
        console.print(f"  UB Knowledge: {original_report.error_type.value}")

        # ----- Phase C+D: Main fix loop -----
        current_code = source_code
        current_report = original_report
        reflection: ReflectionResult | None = None
        all_reflections: list[ReflectionResult] = []

        for iteration in range(1, self._config.max_iterations + 1):
            console.print(f"\n[bold yellow]Iteration {iteration}/{self._config.max_iterations}[/bold yellow]")

            # Reflection (from iteration 2 onwards)
            if iteration > 1 and self._reflection_agent and history.attempts:
                console.print("  [magenta]Reflection Agent[/magenta] analyzing previous failure...")
                last = history.attempts[-1]
                reflection = self._reflection_agent.reflect(
                    original_code=current_code,
                    attempted_code=last.fixed_code,
                    plan=last.plan,
                    miri_result=last.miri_report,
                    fix_status=last.status.value,
                    previous_reflections=all_reflections,
                )
                all_reflections.append(reflection)
                console.print(f"  Reflection: {reflection.next_step_suggestion[:100]}...")

            # Update context
            ctx = self._ctx_assembler.update_for_iteration(
                ctx, current_code, current_report, history.attempts, reflection,
            )

            # Plan
            console.print("  [cyan]Plan Agent[/cyan] generating fix plan...")
            plan = self._plan_agent.generate_plan(ctx)
            strategy_preview = plan.strategy[:120] + "..." if len(plan.strategy) > 120 else plan.strategy
            console.print(f"  Plan: {strategy_preview}")

            # Fix — generate N candidates
            console.print(f"  [cyan]Fix Agent[/cyan] generating {self._config.num_candidates} candidates...")
            raw_codes = self._fix_agent.generate_multiple(
                source_code=current_code,
                miri_report=current_report,
                plan=plan,
                previous_attempts=history.attempts,
                temperatures=self._config.candidate_temperatures[:self._config.num_candidates],
            )

            # Inner loop: compile check each candidate
            candidates: list[FixCandidate] = []
            for idx, code in enumerate(raw_codes):
                temp = self._config.candidate_temperatures[idx] if idx < len(self._config.candidate_temperatures) else 0.5
                candidate = FixCandidate(code=code, temperature=temp)
                candidate = self._compile_check_loop(candidate, test_code)
                if candidate.compile_passed:
                    candidates.append(candidate)
                else:
                    console.print(f"    Candidate {idx + 1}: [red]compile failed[/red]")

            if not candidates:
                console.print("  [red]All candidates failed to compile[/red]")
                attempt = FixAttempt(
                    iteration=iteration, plan=plan,
                    original_code=current_code, fixed_code=raw_codes[0] if raw_codes else "",
                    miri_report=current_report,
                    status=FixStatus.COMPILE_ERROR,
                    num_candidates=len(raw_codes),
                )
                history.attempts.append(attempt)
                continue

            # Critic: evaluate all compile-passing candidates
            console.print(f"  [cyan]Critic[/cyan] evaluating {len(candidates)} candidate(s)...")
            for c in candidates:
                self._critic.evaluate_candidate(c, test_code, source_code, original_report)

            best = MultiDimensionalCritic.select_best(candidates)
            if not best:
                continue

            console.print(f"  Best candidate: {best.score.summary}")

            attempt = FixAttempt(
                iteration=iteration, plan=plan,
                original_code=current_code, fixed_code=best.code,
                miri_report=best.miri_report,
                status=best.status,
                score=best.score,
                reflection=reflection,
                num_candidates=len(raw_codes),
            )
            history.attempts.append(attempt)

            console.print(f"  Status: [bold]{best.status.value}[/bold]")
            console.print(f"  Miri:   {best.miri_report.summary}")

            if best.status == FixStatus.MIRI_PASSED:
                console.print("\n[bold green]SUCCESS — UB fixed![/bold green]")
                self._run_experience(history)
                return history

            if best.status == FixStatus.SCORE_DROPPED:
                console.print("  [red]Score dropped, discarding candidate[/red]")
                continue

            # Update for next iteration
            if best.status in (FixStatus.ERROR_TYPE_CHANGED, FixStatus.SAME_ERROR):
                current_code = best.code
                current_report = best.miri_report

        console.print(f"\n[bold red]FAILED — max iterations ({self._config.max_iterations}) reached[/bold red]")
        return history

    # ===================================================================
    # Public API: single-file mode
    # ===================================================================

    def run_single_file(
        self,
        source_code: str,
        filename: str = "<inline>",
        skip_hallucination: bool = False,
    ) -> FixHistory:
        console.print(Panel(f"[bold]HaluRust v2 — {filename}[/bold]", style="cyan"))

        miri_flags = parse_miri_flags(source_code)
        clean_source = _strip_miri_annotations(source_code)

        # Phase A: Detection
        console.print("\n[bold yellow]Phase A:[/bold yellow] Running Miri on original code...")
        original_report = run_miri_single_file(clean_source, self._config, extra_miri_flags=miri_flags)
        console.print(f"  Result: {original_report.summary}")

        if original_report.passed:
            console.print("[green]No UB detected — nothing to fix![/green]")
            return FixHistory(
                source_file=filename, test_file="",
                original_code=clean_source, original_report=original_report,
            )

        history = FixHistory(
            source_file=filename, test_file="",
            original_code=clean_source, original_report=original_report,
        )

        # Phase B: Context Construction
        console.print("\n[bold yellow]Phase B:[/bold yellow] Building repair context...")

        hallucinated = ""
        if self._config.enable_hallucination and not skip_hallucination:
            console.print("  [dim]Generating hallucinated fix reference...[/dim]")
            hallucinated = self._hallucination_agent.generate(clean_source, original_report)

        ctx = self._ctx_assembler.assemble(
            source_code=clean_source,
            test_code="",
            miri_report=original_report,
            hallucinated_code=hallucinated,
        )

        if ctx.few_shot_examples:
            console.print(f"  Retrieved {len(ctx.few_shot_examples)} few-shot examples")
        console.print(f"  Error localized to: {ctx.localized_error.function_name or 'unknown'} (L{ctx.localized_error.error_line})")

        # Phase C+D: Main fix loop
        current_code = clean_source
        current_report = original_report
        reflection: ReflectionResult | None = None
        all_reflections: list[ReflectionResult] = []

        for iteration in range(1, self._config.max_iterations + 1):
            console.print(f"\n[bold yellow]Iteration {iteration}/{self._config.max_iterations}[/bold yellow]")

            # Reflection
            if iteration > 1 and self._reflection_agent and history.attempts:
                console.print("  [magenta]Reflection Agent[/magenta] analyzing previous failure...")
                last = history.attempts[-1]
                reflection = self._reflection_agent.reflect(
                    original_code=current_code,
                    attempted_code=last.fixed_code,
                    plan=last.plan,
                    miri_result=last.miri_report,
                    fix_status=last.status.value,
                    previous_reflections=all_reflections,
                )
                all_reflections.append(reflection)
                console.print(f"  Reflection: {reflection.next_step_suggestion[:100]}...")

            ctx = self._ctx_assembler.update_for_iteration(
                ctx, current_code, current_report, history.attempts, reflection,
            )

            # Plan
            console.print("  [cyan]Plan Agent[/cyan] generating fix plan...")
            plan = self._plan_agent.generate_plan(ctx)
            strategy_preview = plan.strategy[:120] + "..." if len(plan.strategy) > 120 else plan.strategy
            console.print(f"  Plan: {strategy_preview}")

            # Fix — multi-candidate
            console.print(f"  [cyan]Fix Agent[/cyan] generating {self._config.num_candidates} candidates...")
            raw_codes = self._fix_agent.generate_multiple(
                source_code=current_code,
                miri_report=current_report,
                plan=plan,
                previous_attempts=history.attempts,
                temperatures=self._config.candidate_temperatures[:self._config.num_candidates],
            )

            # Inner loop: compile check
            candidates: list[FixCandidate] = []
            for idx, code in enumerate(raw_codes):
                temp = self._config.candidate_temperatures[idx] if idx < len(self._config.candidate_temperatures) else 0.5
                candidate = FixCandidate(code=code, temperature=temp)
                candidate = self._compile_check_loop_single(candidate)
                if candidate.compile_passed:
                    candidates.append(candidate)
                else:
                    console.print(f"    Candidate {idx + 1}: [red]compile failed[/red]")

            if not candidates:
                console.print("  [red]All candidates failed to compile[/red]")
                attempt = FixAttempt(
                    iteration=iteration, plan=plan,
                    original_code=current_code, fixed_code=raw_codes[0] if raw_codes else "",
                    miri_report=current_report,
                    status=FixStatus.COMPILE_ERROR,
                    num_candidates=len(raw_codes),
                )
                history.attempts.append(attempt)
                continue

            # Critic: evaluate
            console.print(f"  [cyan]Critic[/cyan] evaluating {len(candidates)} candidate(s)...")
            for c in candidates:
                status, miri_rep, score = self._critic.evaluate_single_file(
                    c.code, clean_source, original_report, extra_miri_flags=miri_flags,
                )
                c.miri_report = miri_rep
                c.score = score
                c.status = status

            best = MultiDimensionalCritic.select_best(candidates)
            if not best:
                continue

            console.print(f"  Best candidate: {best.score.summary}")

            attempt = FixAttempt(
                iteration=iteration, plan=plan,
                original_code=current_code, fixed_code=best.code,
                miri_report=best.miri_report,
                status=best.status,
                score=best.score,
                reflection=reflection,
                num_candidates=len(raw_codes),
            )
            history.attempts.append(attempt)

            console.print(f"  Status: [bold]{best.status.value}[/bold]")
            console.print(f"  Miri:   {best.miri_report.summary}")

            if best.status == FixStatus.MIRI_PASSED:
                console.print("\n[bold green]SUCCESS — UB fixed![/bold green]")
                self._run_experience(history)
                return history

            if best.status == FixStatus.SCORE_DROPPED:
                console.print("  [red]Score dropped, discarding candidate[/red]")
                continue

            if best.status in (FixStatus.ERROR_TYPE_CHANGED, FixStatus.SAME_ERROR):
                current_code = best.code
                current_report = best.miri_report

        console.print(f"\n[bold red]FAILED — max iterations ({self._config.max_iterations}) reached[/bold red]")
        return history

    # ===================================================================
    # Inner loop: compile check + fix
    # ===================================================================

    def _compile_check_loop(self, candidate: FixCandidate, test_code: str) -> FixCandidate:
        """Inner loop: try cargo check, fix compile errors up to N retries."""
        for retry in range(self._config.compile_fix_retries + 1):
            result = self._compile_checker.check(candidate.code, test_code)
            if result.success:
                candidate.compile_passed = True
                return candidate
            if retry < self._config.compile_fix_retries:
                candidate.code = self._fix_agent.fix_compile_error(
                    candidate.code, result.stderr,
                )
        candidate.compile_passed = False
        candidate.compile_errors = result.stderr
        return candidate

    def _compile_check_loop_single(self, candidate: FixCandidate) -> FixCandidate:
        """Inner loop for single-file mode."""
        for retry in range(self._config.compile_fix_retries + 1):
            result = self._compile_checker.check_single_file(candidate.code)
            if result.success:
                candidate.compile_passed = True
                return candidate
            if retry < self._config.compile_fix_retries:
                candidate.code = self._fix_agent.fix_compile_error(
                    candidate.code, result.stderr,
                )
        candidate.compile_passed = False
        candidate.compile_errors = result.stderr
        return candidate

    # ===================================================================
    # Phase E: Experience accumulation
    # ===================================================================

    def _run_experience(self, history: FixHistory) -> None:
        """Run post-fix experience accumulation if enabled."""
        if not self._experience:
            return
        try:
            console.print("\n[dim]Phase E: Accumulating experience...[/dim]")
            exp = self._experience.process_success(history)
            if exp:
                console.print(f"  [dim]Explanation: {exp.explanation[:100]}...[/dim]")
                console.print(f"  [dim]RAG library updated ({self._rag.size} examples)[/dim]")
        except Exception as e:
            console.print(f"  [dim red]Experience accumulation failed: {e}[/dim red]")


# ===================================================================
# Utility
# ===================================================================

def _strip_miri_annotations(source: str) -> str:
    """Remove miri test annotations (//~ ERROR, //@compile-flags, etc.) from source."""
    lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("//@") or stripped.startswith("// @"):
            continue
        if stripped.startswith("//~"):
            continue
        line = re.sub(r"\s*//~.*$", "", line)
        lines.append(line)
    return "\n".join(lines)
