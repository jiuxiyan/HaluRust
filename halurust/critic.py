"""Critic module: evaluate fix candidates by re-running Miri."""

from __future__ import annotations

from .config import HaluRustConfig
from .miri_runner import run_miri
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
