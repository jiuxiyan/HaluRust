#!/usr/bin/env python3
"""Build RAG example library by running HaluRust pipeline on selected miri tests.

Features:
- Incremental: saves progress after each file, safe to interrupt and resume
- Organizes output into ub_example_library/ with original, stderr, and fixed code
- Generates index.json for the RAG module to load
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).parent
SELECTION_FILE = PROJECT_ROOT / "selected_tests.json"
PROGRESS_FILE = PROJECT_ROOT / "rag_build_progress.json"
LIBRARY_DIR = PROJECT_ROOT / "ub_example_library"
FAIL_DIR = PROJECT_ROOT / "miri_official_tests" / "fail"


def load_env():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"completed": {}, "started_at": datetime.now().isoformat()}


def save_progress(progress: dict):
    progress["updated_at"] = datetime.now().isoformat()
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


def classify_error_type(stderr_text: str) -> str:
    """Determine UB category from miri stderr output."""
    from halurust.miri_runner import classify_error
    from halurust.models import MiriErrorType
    err_type = classify_error(stderr_text)
    return err_type.value


def get_stderr_content(test_entry: dict) -> str:
    """Get the .stderr content from miri's expected output files."""
    stderr_files = test_entry.get("stderr_files", [])
    if stderr_files:
        for sf in stderr_files:
            p = Path(sf)
            if p.exists():
                return p.read_text(errors='replace')
    return ""


def save_example(category: str, name: str, original_code: str, stderr_content: str,
                 fixed_code: str, error_type: str, miri_error_msg: str):
    """Save a successful fix as a RAG example."""
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name.replace('.rs', ''))
    example_dir = LIBRARY_DIR / category / safe_name
    example_dir.mkdir(parents=True, exist_ok=True)

    (example_dir / "original.rs").write_text(original_code)
    (example_dir / "fixed.rs").write_text(fixed_code)
    (example_dir / "miri_stderr.txt").write_text(stderr_content)

    metadata = {
        "name": name,
        "category": category,
        "error_type": error_type,
        "error_message": miri_error_msg,
    }
    (example_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))


def build_library_index():
    """Scan ub_example_library/ and build index.json for RAG loading."""
    examples = []
    for meta_file in sorted(LIBRARY_DIR.rglob("metadata.json")):
        example_dir = meta_file.parent
        metadata = json.loads(meta_file.read_text())
        original = (example_dir / "original.rs").read_text() if (example_dir / "original.rs").exists() else ""
        fixed = (example_dir / "fixed.rs").read_text() if (example_dir / "fixed.rs").exists() else ""
        stderr = (example_dir / "miri_stderr.txt").read_text() if (example_dir / "miri_stderr.txt").exists() else ""

        examples.append({
            "name": metadata.get("name", example_dir.name),
            "category": metadata.get("category", example_dir.parent.name),
            "error_type": metadata.get("error_type", "unknown"),
            "error_message": metadata.get("error_message", ""),
            "buggy_code": original,
            "fixed_code": fixed,
            "error_report": stderr,
            "dir": str(example_dir.relative_to(LIBRARY_DIR)),
        })

    index = {
        "total": len(examples),
        "built_at": datetime.now().isoformat(),
        "examples": examples,
    }
    (LIBRARY_DIR / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False))
    return len(examples)


def run_pipeline_on_file(pipeline, source_code: str, filename: str):
    """Run the single-file pipeline and return (history, elapsed)."""
    start = time.time()
    history = pipeline.run_single_file(
        source_code=source_code,
        filename=filename,
        skip_hallucination=True,
    )
    elapsed = time.time() - start
    return history, elapsed


def main():
    load_env()

    api_key = os.environ.get("API_KEY", "")
    base_url = os.environ.get("BASE_URL")
    model = os.environ.get("MODEL", "gpt-4o")

    if not api_key:
        console.print("[red]API_KEY not set[/red]")
        sys.exit(1)

    from halurust.config import HaluRustConfig
    from halurust.pipeline import HaluRustPipeline

    config = HaluRustConfig(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_iterations=3,
        temperature=0.3,
        miri_timeout=60,
        num_candidates=1,  # single candidate for library building speed
        enable_reflection=True,
        enable_clippy=False,  # skip clippy during library building
        enable_semantic_check=False,
        enable_experience_accumulation=False,
    )

    pipeline = HaluRustPipeline(config)

    selection = json.loads(SELECTION_FILE.read_text())
    files = selection["files"]
    progress = load_progress()
    completed = progress["completed"]

    remaining = [f for f in files if f["rel_path"] not in completed]
    done_count = len(completed)

    console.print(f"\n[bold]Building RAG Library[/bold]")
    console.print(f"  Total selected: {len(files)}")
    console.print(f"  Already completed: {done_count}")
    console.print(f"  Remaining: {len(remaining)}")
    console.print(f"  Model: {model}\n")

    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    success_count = sum(1 for v in completed.values() if v.get("succeeded"))
    fail_count = done_count - success_count
    start_all = time.time()

    for i, entry in enumerate(remaining, 1):
        rel_path = entry["rel_path"]
        category = entry["category"]
        source_path = Path(entry["path"])
        filename = source_path.name

        console.rule(f"[bold blue][{done_count + i}/{len(files)}] {rel_path}[/bold blue]")

        if not source_path.exists():
            console.print(f"[red]File not found: {source_path}[/red]")
            completed[rel_path] = {"succeeded": False, "error": "file_not_found"}
            save_progress(progress)
            continue

        source_code = source_path.read_text(errors='replace')
        stderr_content = get_stderr_content(entry)

        try:
            history, elapsed = run_pipeline_on_file(pipeline, source_code, filename)

            result = {
                "succeeded": history.succeeded,
                "iterations": len(history.attempts),
                "error_type": history.original_report.error_type.value,
                "error_message": history.original_report.error_message[:200],
                "elapsed_seconds": round(elapsed, 1),
            }

            if history.succeeded and history.final_code:
                actual_stderr = history.original_report.raw_stderr
                if not stderr_content:
                    stderr_content = actual_stderr

                save_example(
                    category=category,
                    name=filename,
                    original_code=source_code,
                    stderr_content=stderr_content,
                    fixed_code=history.final_code,
                    error_type=history.original_report.error_type.value,
                    miri_error_msg=history.original_report.error_message[:300],
                )
                result["saved"] = True
                success_count += 1
                console.print(f"  [green]Saved to ub_example_library/{category}/[/green]")
            else:
                fail_count += 1
                if history.attempts:
                    last = history.attempts[-1]
                    result["final_status"] = last.status.value

            completed[rel_path] = result
            save_progress(progress)

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            completed[rel_path] = {"succeeded": False, "error": str(e)[:200]}
            fail_count += 1
            save_progress(progress)

    total_time = time.time() - start_all

    # Build index
    idx_count = build_library_index()
    console.print(f"\n[bold green]Library index built: {idx_count} examples[/bold green]")

    # Summary
    table = Table(title="RAG Library Build Summary", show_lines=True)
    table.add_column("Category", style="cyan")
    table.add_column("Success", justify="center", style="green")
    table.add_column("Failed", justify="center", style="red")

    cat_stats = {}
    for f in files:
        cat = f["category"]
        rel = f["rel_path"]
        if cat not in cat_stats:
            cat_stats[cat] = {"success": 0, "fail": 0}
        if rel in completed:
            if completed[rel].get("succeeded"):
                cat_stats[cat]["success"] += 1
            else:
                cat_stats[cat]["fail"] += 1

    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        table.add_row(cat, str(s["success"]), str(s["fail"]))

    console.print(table)
    console.print(f"\n[bold]Total: {success_count} succeeded, {fail_count} failed[/bold]")
    console.print(f"Time for this run: {total_time:.1f}s")
    console.print(f"Library saved to: {LIBRARY_DIR}")


if __name__ == "__main__":
    main()
