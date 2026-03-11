#!/usr/bin/env python3
"""Pilot study: run HaluRust pipeline on sample UB cases."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

from halurust.config import HaluRustConfig
from halurust.pipeline import HaluRustPipeline

console = Console()

CASES_DIR = Path(__file__).parent / "cases"
RESULTS_DIR = Path(__file__).parent / "results"

CASES = [
    ("case1_use_after_free", "Use-After-Free via raw pointer"),
    ("case2_out_of_bounds", "Out-of-bounds pointer arithmetic"),
    ("case3_uninitialized", "Uninitialized memory read"),
    ("case4_stacked_borrows", "Stacked Borrows violation"),
    ("case5_dangling_ref", "Dangling reference via Vec realloc"),
]


def load_case(name: str) -> tuple[str, str]:
    source = (CASES_DIR / f"{name}.rs").read_text()
    # Test files follow the pattern caseN_test.rs
    case_num = name.split("_")[0]  # e.g. "case1"
    test = (CASES_DIR / f"{case_num}_test.rs").read_text()
    return source, test


def run_single(name: str, desc: str, config: HaluRustConfig, mock: bool = False) -> dict:
    console.print(f"\n{'='*60}")
    console.print(f"[bold magenta]Case: {desc}[/bold magenta] ({name})")
    console.print(f"{'='*60}")

    source, test = load_case(name)
    pipeline = HaluRustPipeline(config, mock=mock)
    history = pipeline.run(source, test)

    result = {
        "case": name,
        "description": desc,
        "original_error": history.original_report.error_type.value,
        "succeeded": history.succeeded,
        "iterations": len(history.attempts),
        "final_code": history.final_code,
        "attempts": [
            {
                "iteration": a.iteration,
                "status": a.status.value,
                "miri_summary": a.miri_report.summary,
            }
            for a in history.attempts
        ],
    }
    return result


def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", None)
    model = os.environ.get("HALURUST_MODEL", "gpt-4o")

    use_mock = not api_key or "--mock" in sys.argv
    if use_mock:
        console.print("[yellow]No OPENAI_API_KEY set (or --mock flag used). Running in MOCK mode.[/yellow]")
        api_key = api_key or "mock-key"

    config = HaluRustConfig(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_iterations=3,
        temperature=0.3,
        num_candidates=2,  # fewer candidates for pilot study speed
        enable_clippy=not use_mock,
        enable_semantic_check=not use_mock,
        enable_reflection=True,
        enable_experience_accumulation=not use_mock,
    )

    argv_cases = [a for a in sys.argv[1:] if not a.startswith("--")]
    cases_to_run = (
        [(n, d) for n, d in CASES if n in argv_cases]
        if argv_cases
        else CASES
    )

    if not cases_to_run:
        console.print(f"[red]No matching cases. Available: {[n for n, _ in CASES]}[/red]")
        sys.exit(1)

    results = []
    for name, desc in cases_to_run:
        result = run_single(name, desc, config, mock=use_mock)
        results.append(result)

    # Summary table
    console.print(f"\n\n{'='*60}")
    console.print("[bold]PILOT STUDY RESULTS[/bold]")
    console.print(f"{'='*60}\n")

    table = Table(title="HaluRust Pilot Study Summary")
    table.add_column("Case", style="cyan")
    table.add_column("UB Type", style="yellow")
    table.add_column("Fixed?", style="bold")
    table.add_column("Iterations", justify="right")

    for r in results:
        fixed = "[green]YES[/green]" if r["succeeded"] else "[red]NO[/red]"
        table.add_row(r["description"], r["original_error"], fixed, str(r["iterations"]))

    console.print(table)

    success_count = sum(1 for r in results if r["succeeded"])
    console.print(f"\nSuccess rate: {success_count}/{len(results)} ({100*success_count/len(results):.0f}%)")

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"pilot_results_{timestamp}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    console.print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
