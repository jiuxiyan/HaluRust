#!/usr/bin/env python3
"""Batch runner: test HaluRust pipeline against miri tests/fail dataset."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from halurust.config import HaluRustConfig
from halurust.pipeline import HaluRustPipeline

console = Console()


def load_env():
    """Load .env file manually (no external dependency needed)."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def collect_test_files(test_dir: str) -> list[Path]:
    d = Path(test_dir)
    if not d.exists():
        console.print(f"[red]Test directory not found: {test_dir}[/red]")
        sys.exit(1)
    files = sorted(d.glob("*.rs"))
    if not files:
        console.print(f"[red]No .rs files found in {test_dir}[/red]")
        sys.exit(1)
    return files


def run_batch(
    test_dir: str = "miri_tests/fail",
    max_files: int | None = None,
    max_iterations: int = 3,
    output_dir: str = "miri_test_results",
):
    load_env()

    api_key = os.environ.get("API_KEY", "")
    base_url = os.environ.get("BASE_URL", None)
    model = os.environ.get("MODEL", "gpt-4o")

    if not api_key:
        console.print("[red]API_KEY not set in .env[/red]")
        sys.exit(1)

    config = HaluRustConfig(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_iterations=max_iterations,
        temperature=0.3,
        miri_timeout=60,
    )

    pipeline = HaluRustPipeline(config)
    test_files = collect_test_files(test_dir)

    if max_files:
        test_files = test_files[:max_files]

    console.print(f"\n[bold]Running HaluRust on {len(test_files)} miri test files[/bold]")
    console.print(f"  Model: {model}")
    console.print(f"  Max iterations per file: {max_iterations}")
    console.print(f"  Test dir: {test_dir}\n")

    os.makedirs(output_dir, exist_ok=True)
    results = []
    start_all = time.time()

    for i, test_file in enumerate(test_files, 1):
        console.rule(f"[bold blue]File {i}/{len(test_files)}: {test_file.name}[/bold blue]")
        source_code = test_file.read_text()

        start = time.time()
        try:
            history = pipeline.run_single_file(
                source_code=source_code,
                filename=test_file.name,
                skip_hallucination=True,
            )

            elapsed = time.time() - start
            result = {
                "file": test_file.name,
                "original_error_type": history.original_report.error_type.value,
                "original_error_msg": history.original_report.error_message,
                "succeeded": history.succeeded,
                "iterations": len(history.attempts),
                "final_status": history.attempts[-1].status.value if history.attempts else "no_ub",
                "elapsed_seconds": round(elapsed, 1),
            }

            if history.succeeded and history.final_code:
                fixed_path = Path(output_dir) / f"fixed_{test_file.name}"
                fixed_path.write_text(history.final_code)
                result["fixed_file"] = str(fixed_path)

            results.append(result)

        except Exception as e:
            elapsed = time.time() - start
            console.print(f"[red]Error processing {test_file.name}: {e}[/red]")
            results.append({
                "file": test_file.name,
                "original_error_type": "error",
                "succeeded": False,
                "iterations": 0,
                "final_status": f"pipeline_error: {str(e)[:200]}",
                "elapsed_seconds": round(elapsed, 1),
            })

    total_time = time.time() - start_all

    # Print summary table
    console.print("\n")
    table = Table(title="HaluRust Batch Results", show_lines=True)
    table.add_column("File", style="cyan", max_width=40)
    table.add_column("UB Type", style="yellow")
    table.add_column("Result", style="bold")
    table.add_column("Iters", justify="center")
    table.add_column("Time (s)", justify="right")

    for r in results:
        status_str = "[green]FIXED[/green]" if r["succeeded"] else f"[red]{r['final_status']}[/red]"
        table.add_row(
            r["file"],
            r.get("original_error_type", "?"),
            status_str,
            str(r["iterations"]),
            str(r["elapsed_seconds"]),
        )

    console.print(table)

    success_count = sum(1 for r in results if r["succeeded"])
    console.print(f"\n[bold]Summary: {success_count}/{len(results)} fixed[/bold]")
    console.print(f"Total time: {total_time:.1f}s")

    # Save JSON report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(output_dir) / f"batch_results_{timestamp}.json"
    report_data = {
        "timestamp": timestamp,
        "model": model,
        "max_iterations": max_iterations,
        "total_files": len(results),
        "success_count": success_count,
        "total_time_seconds": round(total_time, 1),
        "results": results,
    }
    report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False))
    console.print(f"Report saved to: {report_path}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch test HaluRust on miri tests/fail")
    parser.add_argument("--test-dir", default="miri_tests/fail", help="Directory with .rs test files")
    parser.add_argument("--max-files", type=int, default=None, help="Limit number of files")
    parser.add_argument("--max-iter", type=int, default=3, help="Max fix iterations per file")
    parser.add_argument("--output-dir", default="miri_test_results", help="Output directory")
    args = parser.parse_args()

    run_batch(
        test_dir=args.test_dir,
        max_files=args.max_files,
        max_iterations=args.max_iter,
        output_dir=args.output_dir,
    )
