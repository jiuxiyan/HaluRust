"""Run Miri on Rust code and parse the error report."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from .config import HaluRustConfig
from .models import MiriErrorType, MiriReport


ERROR_PATTERNS: list[tuple[re.Pattern, MiriErrorType]] = [
    (re.compile(r"freed.*dangling|dangling.*freed|has been freed", re.I), MiriErrorType.USE_AFTER_FREE),
    (re.compile(r"out.of.bounds|beyond the end of", re.I), MiriErrorType.OUT_OF_BOUNDS),
    (re.compile(r"null pointer|invalid.*deref|dereferencing pointer", re.I), MiriErrorType.INVALID_DEREF),
    (re.compile(r"uninitialized|not initialized", re.I), MiriErrorType.UNINITIALIZED),
    (re.compile(r"data race", re.I), MiriErrorType.DATA_RACE),
    (re.compile(r"alignment|misaligned", re.I), MiriErrorType.INVALID_ALIGNMENT),
    (re.compile(r"dangling reference|borrow of .* deallocated", re.I), MiriErrorType.DANGLING_REFERENCE),
    (re.compile(r"Stacked Borrows|stacked borrows|reborrow .* permission", re.I), MiriErrorType.STACKED_BORROWS),
    (re.compile(r"Tree Borrows|tree borrows", re.I), MiriErrorType.TREE_BORROWS),
    (re.compile(r"ptr.to.int cast|int.to.ptr cast", re.I), MiriErrorType.INT_TO_PTR_CAST),
    (re.compile(r"memory leak|the following memory was leaked", re.I), MiriErrorType.MEMORY_LEAK),
]


def classify_error(stderr: str) -> MiriErrorType:
    for pattern, error_type in ERROR_PATTERNS:
        if pattern.search(stderr):
            return error_type
    return MiriErrorType.UNKNOWN


def extract_error_details(stderr: str) -> tuple[str, str, str]:
    """Extract error message, location, and help text from Miri stderr."""
    error_msg = ""
    location = ""
    help_text = ""

    for line in stderr.splitlines():
        if "Undefined Behavior:" in line:
            error_msg = line.strip()
        elif "help:" in line.lower():
            help_text += line.strip() + "\n"
        elif re.match(r"\s*-->\s+", line):
            location = line.strip()

    return error_msg, location, help_text.strip()


def run_miri(
    source_code: str,
    test_code: str,
    config: HaluRustConfig,
    project_dir: Path | None = None,
) -> MiriReport:
    """Run Miri test on given Rust source + test code.

    If project_dir is provided, use it directly. Otherwise create a temp Cargo project.
    """
    if project_dir is None:
        return _run_miri_in_temp(source_code, test_code, config)
    return _run_miri_in_project(project_dir, config)


def _run_miri_in_temp(source_code: str, test_code: str, config: HaluRustConfig) -> MiriReport:
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "ub_check"
        _init_cargo_project(project_dir, source_code, test_code)
        return _run_miri_in_project(project_dir, config)


def _init_cargo_project(project_dir: Path, source_code: str, test_code: str) -> None:
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True)

    cargo_toml = project_dir / "Cargo.toml"
    cargo_toml.write_text(
        '[package]\nname = "ub_check"\nversion = "0.1.0"\nedition = "2021"\n'
    )

    full_code = source_code.rstrip("\n") + "\n\n" + test_code
    (src_dir / "lib.rs").write_text(full_code)


def _run_miri_in_project(project_dir: Path, config: HaluRustConfig) -> MiriReport:
    try:
        result = subprocess.run(
            ["cargo", "+nightly", "miri", "test"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=config.miri_timeout,
            env=_miri_env(),
        )
    except subprocess.TimeoutExpired:
        return MiriReport(
            passed=False,
            error_type=MiriErrorType.UNKNOWN,
            raw_stderr="Miri timed out",
            error_message="Miri execution timed out",
        )
    except FileNotFoundError:
        return MiriReport(
            passed=False,
            error_type=MiriErrorType.UNKNOWN,
            raw_stderr="cargo/miri not found",
            error_message="cargo +nightly miri not found. Install via: rustup +nightly component add miri",
        )

    stderr = result.stderr
    if result.returncode == 0 and "Undefined Behavior" not in stderr:
        return MiriReport(passed=True, raw_stderr=stderr)

    error_type = classify_error(stderr)
    error_msg, location, help_text = extract_error_details(stderr)

    return MiriReport(
        passed=False,
        error_type=error_type,
        raw_stderr=stderr,
        error_message=error_msg,
        error_location=location,
        help_text=help_text,
    )


def _miri_env() -> dict[str, str]:
    import os
    env = os.environ.copy()
    env["MIRIFLAGS"] = env.get("MIRIFLAGS", "-Zmiri-disable-isolation")
    return env
