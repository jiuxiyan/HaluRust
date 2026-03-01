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
    (re.compile(r"out.of.bounds|beyond the end of|in-bounds pointer arithmetic failed", re.I), MiriErrorType.OUT_OF_BOUNDS),
    (re.compile(r"null (pointer|reference)|invalid.*deref|dereferencing pointer|null reference", re.I), MiriErrorType.INVALID_DEREF),
    (re.compile(r"uninitialized|not initialized", re.I), MiriErrorType.UNINITIALIZED),
    (re.compile(r"data race", re.I), MiriErrorType.DATA_RACE),
    (re.compile(r"alignment|misaligned", re.I), MiriErrorType.INVALID_ALIGNMENT),
    (re.compile(r"dangling (reference|pointer)|borrow of .* deallocated|has no provenance|does not exist in the borrow stack", re.I), MiriErrorType.DANGLING_REFERENCE),
    (re.compile(r"Stacked Borrows|stacked borrows|reborrow .* permission|SharedReadOnly permission", re.I), MiriErrorType.STACKED_BORROWS),
    (re.compile(r"Tree Borrows|tree borrows|is forbidden", re.I), MiriErrorType.TREE_BORROWS),
    (re.compile(r"ptr.to.int cast|int.to.ptr cast", re.I), MiriErrorType.INT_TO_PTR_CAST),
    (re.compile(r"memory leak|the following memory was leaked", re.I), MiriErrorType.MEMORY_LEAK),
]


def classify_error(stderr: str) -> MiriErrorType:
    """Classify the Miri error. Only looks at lines containing 'error' or 'Undefined Behavior'
    to avoid false matches against MIRIFLAGS or compiler arguments in stderr."""
    relevant_lines = []
    for line in stderr.splitlines():
        lower = line.lower()
        if any(kw in lower for kw in ["undefined behavior", "error", "memory leaked", "leaked", "dangling"]):
            relevant_lines.append(line)
    relevant_text = "\n".join(relevant_lines)
    if not relevant_text:
        relevant_text = stderr

    for pattern, error_type in ERROR_PATTERNS:
        if pattern.search(relevant_text):
            return error_type
    return MiriErrorType.UNKNOWN


def extract_error_details(stderr: str) -> tuple[str, str, str]:
    """Extract error message, location, and help text from Miri stderr."""
    error_msg = ""
    location = ""
    help_text = ""

    for line in stderr.splitlines():
        if "Undefined Behavior:" in line or "error:" in line.lower():
            if not error_msg:
                error_msg = line.strip()
        elif "help:" in line.lower():
            help_text += line.strip() + "\n"
        elif re.match(r"\s*-->\s+", line):
            location = line.strip()

    return error_msg, location, help_text.strip()


def parse_miri_flags(source_code: str) -> list[str]:
    """Extract //@compile-flags from source file comments."""
    flags = []
    for line in source_code.splitlines():
        m = re.match(r"^\s*//\s*@\s*compile-flags:\s*(.+)", line)
        if not m:
            m = re.match(r"^\s*//\s*@\[.*\]\s*compile-flags:\s*(.+)", line)
        if m:
            flags.extend(m.group(1).strip().split())
    return flags


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


def run_miri_single_file(
    source_code: str,
    config: HaluRustConfig,
    extra_miri_flags: list[str] | None = None,
) -> MiriReport:
    """Run Miri on a single-file program (with main()) using `cargo miri run`.

    Uses a persistent workspace directory to avoid temp directory cleanup issues.
    """
    project_dir = config.workspace_dir / "miri_single"
    _init_cargo_bin_project(project_dir, source_code)
    return _run_miri_command(
        project_dir, config,
        command=["cargo", "+nightly", "miri", "run"],
        extra_miri_flags=extra_miri_flags,
    )


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


def _init_cargo_bin_project(project_dir: Path, source_code: str) -> None:
    """Create a cargo binary project (with main.rs) for single-file miri run."""
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    cargo_toml = project_dir / "Cargo.toml"
    cargo_toml.write_text(
        '[package]\nname = "ub_check"\nversion = "0.1.0"\nedition = "2021"\n'
    )

    (src_dir / "main.rs").write_text(source_code)


def _run_miri_in_project(project_dir: Path, config: HaluRustConfig) -> MiriReport:
    return _run_miri_command(project_dir, config, command=["cargo", "+nightly", "miri", "test"])


def _run_miri_command(
    project_dir: Path,
    config: HaluRustConfig,
    command: list[str],
    extra_miri_flags: list[str] | None = None,
) -> MiriReport:
    target_dir = project_dir / "target"
    try:
        result = subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=config.miri_timeout,
            env=_miri_env(extra_miri_flags, target_dir=target_dir),
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
    stdout = result.stdout

    if result.returncode == 0 and "Undefined Behavior" not in stderr and "memory leaked" not in stderr.lower():
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


def _miri_env(extra_flags: list[str] | None = None, target_dir: Path | None = None) -> dict[str, str]:
    import os
    env = os.environ.copy()
    base_flags = "-Zmiri-disable-isolation"
    if extra_flags:
        miri_specific = [f for f in extra_flags if f.startswith("-Zmiri")]
        if miri_specific:
            base_flags = base_flags + " " + " ".join(miri_specific)
    env["MIRIFLAGS"] = base_flags
    if target_dir:
        env["CARGO_TARGET_DIR"] = str(target_dir)
    return env
