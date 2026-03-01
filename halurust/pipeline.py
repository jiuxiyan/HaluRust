"""Main pipeline: orchestrates the iterative fix loop."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from .agents import FixAgent, HallucinationAgent, PlanAgent
from .config import HaluRustConfig
from .critic import Critic, CriticSingleFile
from .llm_client import LLMClient
from .miri_runner import parse_miri_flags, run_miri, run_miri_single_file
from .models import FixAttempt, FixHistory, FixStatus
from .rag import UBExampleLibrary

console = Console()


class HaluRustPipeline:
    def __init__(self, config: HaluRustConfig, mock: bool = False):
        self._config = config
        if mock:
            from .mock_llm import MockLLMClient
            llm = MockLLMClient(config)  # type: ignore[arg-type]
        else:
            llm = LLMClient(config)
        self._plan_agent = PlanAgent(llm)
        self._fix_agent = FixAgent(llm)
        self._hallucination_agent = HallucinationAgent(llm)
        self._critic = Critic(config)
        self._rag = UBExampleLibrary()

    def run(self, source_code: str, test_code: str) -> FixHistory:
        console.print(Panel("[bold]HaluRust Pipeline[/bold]", style="cyan"))

        # Step 1: Initial Miri run
        console.print("\n[bold yellow]Step 1:[/bold yellow] Running Miri on original code...")
        original_report = run_miri(source_code, test_code, self._config)
        console.print(f"  Result: {original_report.summary}")

        if original_report.passed:
            console.print("[green]No UB detected — nothing to fix![/green]")
            return FixHistory(
                source_file="<inline>",
                test_file="<inline>",
                original_code=source_code,
                original_report=original_report,
            )

        history = FixHistory(
            source_file="<inline>",
            test_file="<inline>",
            original_code=source_code,
            original_report=original_report,
        )

        # Step 2: Retrieve few-shot examples (currently empty)
        few_shots = self._rag.retrieve(original_report.error_type.value)
        if few_shots:
            console.print(f"  Retrieved {len(few_shots)} few-shot examples")
        else:
            console.print("  [dim]No few-shot examples available (RAG empty)[/dim]")

        # Step 3: Generate hallucinated fix
        console.print("\n[bold yellow]Step 2:[/bold yellow] Generating hallucinated fix reference...")
        hallucinated = self._hallucination_agent.generate(source_code, original_report)
        console.print("  [dim]Hallucinated fix generated[/dim]")

        # Step 4: Iterative fix loop
        current_code = source_code
        current_report = original_report

        for iteration in range(1, self._config.max_iterations + 1):
            console.print(
                f"\n[bold yellow]Iteration {iteration}/{self._config.max_iterations}[/bold yellow]"
            )

            # Plan
            console.print("  [cyan]Plan Agent[/cyan] generating fix plan...")
            plan = self._plan_agent.generate_plan(
                source_code=current_code,
                miri_report=current_report,
                few_shots=few_shots if few_shots else None,
                hallucinated_code=hallucinated,
            )
            console.print(f"  Plan: {plan.strategy[:120]}..." if len(plan.strategy) > 120 else f"  Plan: {plan.strategy}")

            # Fix
            console.print("  [cyan]Fix Agent[/cyan] generating fixed code...")
            fixed_code = self._fix_agent.generate_fix(
                source_code=current_code,
                miri_report=current_report,
                plan=plan,
                previous_attempts=history.attempts,
            )

            # Evaluate
            console.print("  [cyan]Critic[/cyan] evaluating fix...")
            status, new_report = self._critic.evaluate(
                fixed_code, test_code, original_report
            )

            attempt = FixAttempt(
                iteration=iteration,
                plan=plan,
                original_code=current_code,
                fixed_code=fixed_code,
                miri_report=new_report,
                status=status,
            )
            history.attempts.append(attempt)

            console.print(f"  Status: [bold]{status.value}[/bold]")
            console.print(f"  Miri:   {new_report.summary}")

            if status == FixStatus.MIRI_PASSED:
                console.print("\n[bold green]SUCCESS — UB fixed![/bold green]")
                return history

            if status == FixStatus.SCORE_DROPPED:
                console.print("  [red]Score dropped, discarding candidate[/red]")
                continue

            # Update for next iteration
            if status in (FixStatus.ERROR_TYPE_CHANGED, FixStatus.SAME_ERROR, FixStatus.COMPILE_ERROR):
                current_code = fixed_code
                current_report = new_report

        console.print(f"\n[bold red]FAILED — max iterations ({self._config.max_iterations}) reached[/bold red]")
        return history

    def run_single_file(
        self,
        source_code: str,
        filename: str = "<inline>",
        skip_hallucination: bool = True,
    ) -> FixHistory:
        """Run the pipeline on a single-file program (with main()).

        Uses `cargo miri run` instead of `cargo miri test`.
        Designed for miri tests/fail style files.
        """
        console.print(Panel(f"[bold]HaluRust — {filename}[/bold]", style="cyan"))

        miri_flags = parse_miri_flags(source_code)
        clean_source = _strip_miri_annotations(source_code)

        # Step 1: Initial Miri run to confirm UB
        console.print("\n[bold yellow]Step 1:[/bold yellow] Running Miri on original code...")
        original_report = run_miri_single_file(clean_source, self._config, extra_miri_flags=miri_flags)
        console.print(f"  Result: {original_report.summary}")

        if original_report.passed:
            console.print("[green]No UB detected — nothing to fix![/green]")
            return FixHistory(
                source_file=filename,
                test_file="",
                original_code=clean_source,
                original_report=original_report,
            )

        history = FixHistory(
            source_file=filename,
            test_file="",
            original_code=clean_source,
            original_report=original_report,
        )

        # Step 2: RAG (skipped — library empty)
        few_shots = self._rag.retrieve(original_report.error_type.value)
        if few_shots:
            console.print(f"  Retrieved {len(few_shots)} few-shot examples")
        else:
            console.print("  [dim]No few-shot examples (RAG empty)[/dim]")

        # Step 3: Hallucination (optionally skipped)
        hallucinated = None
        if not skip_hallucination:
            console.print("\n[bold yellow]Step 2:[/bold yellow] Generating hallucinated fix...")
            hallucinated = self._hallucination_agent.generate(clean_source, original_report)
            console.print("  [dim]Hallucinated fix generated[/dim]")
        else:
            console.print("  [dim]Hallucination skipped[/dim]")

        # Step 4: Iterative fix loop
        critic = CriticSingleFile(self._config, extra_miri_flags=miri_flags)
        current_code = clean_source
        current_report = original_report

        for iteration in range(1, self._config.max_iterations + 1):
            console.print(
                f"\n[bold yellow]Iteration {iteration}/{self._config.max_iterations}[/bold yellow]"
            )

            console.print("  [cyan]Plan Agent[/cyan] generating fix plan...")
            plan = self._plan_agent.generate_plan(
                source_code=current_code,
                miri_report=current_report,
                few_shots=few_shots if few_shots else None,
                hallucinated_code=hallucinated,
            )
            console.print(f"  Plan: {plan.strategy[:120]}..." if len(plan.strategy) > 120 else f"  Plan: {plan.strategy}")

            console.print("  [cyan]Fix Agent[/cyan] generating fixed code...")
            fixed_code = self._fix_agent.generate_fix(
                source_code=current_code,
                miri_report=current_report,
                plan=plan,
                previous_attempts=history.attempts,
            )

            console.print("  [cyan]Critic[/cyan] evaluating fix...")
            status, new_report = critic.evaluate(fixed_code, original_report)

            attempt = FixAttempt(
                iteration=iteration,
                plan=plan,
                original_code=current_code,
                fixed_code=fixed_code,
                miri_report=new_report,
                status=status,
            )
            history.attempts.append(attempt)

            console.print(f"  Status: [bold]{status.value}[/bold]")
            console.print(f"  Miri:   {new_report.summary}")

            if status == FixStatus.MIRI_PASSED:
                console.print("\n[bold green]SUCCESS — UB fixed![/bold green]")
                return history

            if status == FixStatus.SCORE_DROPPED:
                console.print("  [red]Score dropped, discarding candidate[/red]")
                continue

            if status in (FixStatus.ERROR_TYPE_CHANGED, FixStatus.SAME_ERROR, FixStatus.COMPILE_ERROR):
                current_code = fixed_code
                current_report = new_report

        console.print(f"\n[bold red]FAILED — max iterations ({self._config.max_iterations}) reached[/bold red]")
        return history


def _strip_miri_annotations(source: str) -> str:
    """Remove miri test annotations (//~ ERROR, //@compile-flags, etc.) from source.

    These annotations are test harness metadata and can confuse the LLM.
    """
    import re
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
