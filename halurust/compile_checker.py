"""Compile Checker — fast cargo check / cargo clippy before running Miri."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import HaluRustConfig


@dataclass
class CompileResult:
    success: bool
    stderr: str = ""
    warnings: int = 0
    errors: int = 0


@dataclass
class ClippyResult:
    success: bool
    stderr: str = ""
    warnings: int = 0
    warning_details: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.warning_details is None:
            self.warning_details = []


class CompileChecker:
    """Runs `cargo check` to quickly validate that code compiles."""

    def __init__(self, config: HaluRustConfig):
        self._config = config

    def check(self, source_code: str, test_code: str = "") -> CompileResult:
        """Check lib + test compilation."""
        project_dir = self._config.workspace_dir / "compile_check"
        _init_cargo_project(project_dir, source_code, test_code)
        return self._run_check(project_dir)

    def check_single_file(self, source_code: str) -> CompileResult:
        """Check a single-file binary program."""
        project_dir = self._config.workspace_dir / "compile_check_single"
        _init_cargo_bin_project(project_dir, source_code)
        return self._run_check(project_dir)

    def _run_check(self, project_dir: Path) -> CompileResult:
        env = os.environ.copy()
        env["CARGO_TARGET_DIR"] = str(project_dir / "target")
        try:
            result = subprocess.run(
                ["cargo", "+nightly", "check"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=self._config.compile_timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return CompileResult(success=False, stderr="Compile check timed out")
        except FileNotFoundError:
            return CompileResult(success=False, stderr="cargo not found")

        stderr = result.stderr
        errors = stderr.count("error[E")
        warnings = stderr.count("warning:")

        return CompileResult(
            success=(result.returncode == 0),
            stderr=stderr,
            warnings=warnings,
            errors=errors,
        )


class ClippyAnalyzer:
    """Runs `cargo clippy` for static analysis scoring."""

    def __init__(self, config: HaluRustConfig):
        self._config = config

    def analyze(self, source_code: str, test_code: str = "") -> ClippyResult:
        project_dir = self._config.workspace_dir / "clippy_check"
        _init_cargo_project(project_dir, source_code, test_code)
        return self._run_clippy(project_dir)

    def analyze_single_file(self, source_code: str) -> ClippyResult:
        project_dir = self._config.workspace_dir / "clippy_check_single"
        _init_cargo_bin_project(project_dir, source_code)
        return self._run_clippy(project_dir)

    def _run_clippy(self, project_dir: Path) -> ClippyResult:
        env = os.environ.copy()
        env["CARGO_TARGET_DIR"] = str(project_dir / "target")
        try:
            result = subprocess.run(
                ["cargo", "+nightly", "clippy", "--", "-W", "clippy::all"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=self._config.clippy_timeout,
                env=env,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ClippyResult(success=False, stderr="clippy unavailable or timed out")

        stderr = result.stderr
        warnings = stderr.count("warning:")

        # Extract individual warning messages
        details = []
        for line in stderr.splitlines():
            if "warning:" in line.lower() and "generated" not in line.lower():
                details.append(line.strip())

        return ClippyResult(
            success=(result.returncode == 0),
            stderr=stderr,
            warnings=warnings,
            warning_details=details,
        )


# ---------------------------------------------------------------------------
# Cargo project scaffolding (shared helpers)
# ---------------------------------------------------------------------------

def _init_cargo_project(project_dir: Path, source_code: str, test_code: str) -> None:
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "Cargo.toml").write_text(
        '[package]\nname = "ub_check"\nversion = "0.1.0"\nedition = "2021"\n'
    )
    full_code = source_code.rstrip("\n") + "\n\n" + test_code if test_code else source_code
    (src_dir / "lib.rs").write_text(full_code)


def _init_cargo_bin_project(project_dir: Path, source_code: str) -> None:
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "Cargo.toml").write_text(
        '[package]\nname = "ub_check"\nversion = "0.1.0"\nedition = "2021"\n'
    )
    (src_dir / "main.rs").write_text(source_code)
