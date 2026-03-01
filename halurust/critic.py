"""Critic module: evaluate fix candidates by re-running Miri."""

from __future__ import annotations

from .config import HaluRustConfig
from .miri_runner import run_miri, run_miri_single_file
from .models import FixStatus, MiriReport


class Critic:
    def __init__(self, config: HaluRustConfig):
        self._config = config

    def evaluate(
        self,
        fixed_code: str,
        test_code: str,
        original_report: MiriReport,
    ) -> tuple[FixStatus, MiriReport]:
        new_report = run_miri(fixed_code, test_code, self._config)

        if new_report.passed:
            return FixStatus.MIRI_PASSED, new_report

        if "error[E" in new_report.raw_stderr:
            return FixStatus.COMPILE_ERROR, new_report

        if new_report.error_type != original_report.error_type:
            return FixStatus.ERROR_TYPE_CHANGED, new_report

        return FixStatus.SAME_ERROR, new_report


class CriticSingleFile:
    """Critic for single-file programs using `cargo miri run`."""

    def __init__(self, config: HaluRustConfig, extra_miri_flags: list[str] | None = None):
        self._config = config
        self._extra_miri_flags = extra_miri_flags

    def evaluate(
        self,
        fixed_code: str,
        original_report: MiriReport,
    ) -> tuple[FixStatus, MiriReport]:
        new_report = run_miri_single_file(fixed_code, self._config, self._extra_miri_flags)

        if new_report.passed:
            return FixStatus.MIRI_PASSED, new_report

        if "error[E" in new_report.raw_stderr:
            return FixStatus.COMPILE_ERROR, new_report

        if new_report.error_type != original_report.error_type:
            return FixStatus.ERROR_TYPE_CHANGED, new_report

        return FixStatus.SAME_ERROR, new_report
