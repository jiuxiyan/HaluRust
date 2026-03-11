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


# ---------------------------------------------------------------------------
# Critic & Scoring
# ---------------------------------------------------------------------------

@dataclass
class CriticScore:
    """Multi-dimensional evaluation score for a fix candidate."""
    miri_passed: bool = False
    static_score: float = 0.0       # clippy-based (0~1, higher = fewer warnings)
    semantic_score: float = 0.0     # LLM-judged semantic preservation (0~1)
    minimal_change_score: float = 0.0  # AST diff based (0~1, higher = smaller change)
    clippy_warnings: int = 0
    unsafe_block_delta: int = 0     # change in number of unsafe blocks (negative = good)

    @property
    def composite(self) -> float:
        """Weighted composite score (only meaningful when miri_passed=False for ranking)."""
        if self.miri_passed:
            return 0.2 * self.static_score + 0.4 * self.semantic_score + 0.4 * self.minimal_change_score
        return 0.2 * self.static_score + 0.4 * self.semantic_score + 0.4 * self.minimal_change_score

    @property
    def summary(self) -> str:
        parts = [f"miri={'PASS' if self.miri_passed else 'FAIL'}"]
        parts.append(f"static={self.static_score:.2f}")
        parts.append(f"semantic={self.semantic_score:.2f}")
        parts.append(f"minimal={self.minimal_change_score:.2f}")
        parts.append(f"composite={self.composite:.2f}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Fix Candidates (multi-candidate generation)
# ---------------------------------------------------------------------------

@dataclass
class FixCandidate:
    """A single fix candidate with its code and evaluation results."""
    code: str
    temperature: float = 0.3
    compile_passed: bool = False
    compile_errors: str = ""
    miri_report: MiriReport = field(default_factory=lambda: MiriReport(passed=False))
    score: CriticScore = field(default_factory=CriticScore)
    status: FixStatus = FixStatus.SAME_ERROR


# ---------------------------------------------------------------------------
# Reflection
# ---------------------------------------------------------------------------

@dataclass
class ReflectionResult:
    """Output from the Reflection Agent after a failed fix attempt."""
    failure_analysis: str = ""
    ineffective_strategies: list[str] = field(default_factory=list)
    next_step_suggestion: str = ""
    raw: str = ""


# ---------------------------------------------------------------------------
# Fix Attempt & History (enhanced)
# ---------------------------------------------------------------------------

@dataclass
class FixAttempt:
    iteration: int
    plan: FixPlan
    original_code: str
    fixed_code: str
    miri_report: MiriReport
    status: FixStatus
    score: CriticScore = field(default_factory=CriticScore)
    reflection: ReflectionResult | None = None
    num_candidates: int = 1


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


# ---------------------------------------------------------------------------
# Error Localization
# ---------------------------------------------------------------------------

@dataclass
class LocalizedError:
    """Error precisely located within the AST."""
    error_line: int = 0
    function_name: str = ""
    function_range: tuple[int, int] = (0, 0)
    code_snippet: str = ""
    unsafe_context: bool = False
    related_variables: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Repair Context (assembled by ContextAssembler)
# ---------------------------------------------------------------------------

@dataclass
class RepairContext:
    """Complete context package assembled for the fix loop."""
    source_code: str = ""
    test_code: str = ""
    miri_report: MiriReport = field(default_factory=lambda: MiriReport(passed=False))
    ast_summary: str = ""
    unsafe_blocks: list[str] = field(default_factory=list)
    borrow_graph: str = ""
    localized_error: LocalizedError = field(default_factory=LocalizedError)
    few_shot_examples: list = field(default_factory=list)
    ub_type_knowledge: str = ""
    hallucinated_code: str = ""
    fix_history: list[FixAttempt] = field(default_factory=list)
    reflection: ReflectionResult | None = None


# ---------------------------------------------------------------------------
# Experience / Accumulation
# ---------------------------------------------------------------------------

@dataclass
class FixExperience:
    """A complete fix experience record for RAG auto-update."""
    original_code: str
    error_report: str
    error_type: str
    fixed_code: str
    explanation: str
    fix_strategy: str
    category: str = ""
    iterations_needed: int = 1
    score: float = 0.0
