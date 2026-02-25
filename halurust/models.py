"""Data models used throughout the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MiriErrorType(str, Enum):
    USE_AFTER_FREE = "use_after_free"
    OUT_OF_BOUNDS = "out_of_bounds"
    INVALID_DEREF = "invalid_deref"
    UNINITIALIZED = "uninitialized_memory"
    DATA_RACE = "data_race"
    INVALID_ALIGNMENT = "invalid_alignment"
    DANGLING_REFERENCE = "dangling_reference"
    STACKED_BORROWS = "stacked_borrows"
    TREE_BORROWS = "tree_borrows"
    INT_TO_PTR_CAST = "int_to_ptr_cast"
    MEMORY_LEAK = "memory_leak"
    UNKNOWN = "unknown"


class FixStatus(str, Enum):
    MIRI_PASSED = "miri_passed"
    SCORE_DROPPED = "score_dropped"
    ERROR_TYPE_CHANGED = "error_type_changed"
    SAME_ERROR = "same_error"
    COMPILE_ERROR = "compile_error"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class MiriReport:
    passed: bool
    error_type: MiriErrorType = MiriErrorType.UNKNOWN
    raw_stderr: str = ""
    error_message: str = ""
    error_location: str = ""
    help_text: str = ""

    @property
    def summary(self) -> str:
        if self.passed:
            return "Miri: PASSED (no UB detected)"
        return f"Miri: FAILED [{self.error_type.value}] {self.error_message}"


@dataclass
class FixPlan:
    analysis: str = ""
    root_cause: str = ""
    strategy: str = ""
    steps: list[str] = field(default_factory=list)
    raw: str = ""


@dataclass
class FixAttempt:
    iteration: int
    plan: FixPlan
    original_code: str
    fixed_code: str
    miri_report: MiriReport
    status: FixStatus


@dataclass
class FixHistory:
    source_file: str
    test_file: str
    original_code: str
    original_report: MiriReport
    attempts: list[FixAttempt] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return any(a.status == FixStatus.MIRI_PASSED for a in self.attempts)

    @property
    def final_code(self) -> str | None:
        for a in reversed(self.attempts):
            if a.status == FixStatus.MIRI_PASSED:
                return a.fixed_code
        return None
