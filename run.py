#!/usr/bin/env python3
"""CLI entry point for HaluRust: fix UB in Rust code using LLMs."""

import argparse
import os
import sys
from pathlib import Path

from rich.console import Console

from halurust.config import HaluRustConfig
from halurust.pipeline import HaluRustPipeline

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="HaluRust: LLM-based Rust Undefined Behavior auto-fixer"
    )
    parser.add_argument("source", type=str, help="Path to the Rust source file with UB")
    parser.add_argument("test", type=str, help="Path to the Rust test file")
    parser.add_argument("--model", default=os.environ.get("HALURUST_MODEL", "gpt-4o"))
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", None))
    parser.add_argument("--max-iter", type=int, default=5)
    parser.add_argument("--output", "-o", type=str, help="Write fixed code to file")

    args = parser.parse_args()

    if not args.api_key:
        console.print("[red]Error: --api-key or OPENAI_API_KEY required[/red]")
        sys.exit(1)

    source_code = Path(args.source).read_text()
    test_code = Path(args.test).read_text()

    config = HaluRustConfig(
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
        max_iterations=args.max_iter,
    )

    pipeline = HaluRustPipeline(config)
    history = pipeline.run(source_code, test_code)

    if history.succeeded and history.final_code:
        if args.output:
            Path(args.output).write_text(history.final_code)
            console.print(f"\n[green]Fixed code written to {args.output}[/green]")
        else:
            console.print("\n[bold green]Fixed code:[/bold green]")
            console.print(f"```rust\n{history.final_code}\n```")
    else:
        console.print("\n[red]Failed to fix the UB within the iteration limit.[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
