"""Multi-Dimensional Critic — evaluate fix candidates across four dimensions.

Dimensions:
  1. Miri Validator     — re-run Miri (mandatory pass/fail)
  2. Clippy Analyzer    — static analysis warning count
  3. Semantic Preserve  — LLM-judged semantic preservation
  4. Minimal Change     — AST diff score
"""

from __future__ import annotations

import logging

from .agents import SemanticPreservationChecker
from .ast_parser import compute_ast_diff_score, count_unsafe_blocks
from .compile_checker import ClippyAnalyzer, ClippyResult
from .config import HaluRustConfig
from .knowledge_graph import is_same_family
from .llm_client import LLMClient
from .miri_runner import run_miri, run_miri_single_file
from .models import CriticScore, FixCandidate, FixStatus, MiriReport

logger = logging.getLogger(__name__)


class MultiDimensionalCritic:
    """Evaluates fix candidates across multiple dimensions and produces a composite score."""

    def __init__(self, config: HaluRustConfig, llm: LLMClient | None = None):
        self._config = config
        self._clippy = ClippyAnalyzer(config) if config.enable_clippy else None
        self._semantic_checker = (
            SemanticPreservationChecker(llm) if config.enable_semantic_check and llm else None
        )

    def evaluate(
        self,
        fixed_code: str,
        test_code: str,
        original_code: str,
        original_report: MiriReport,
    ) -> tuple[FixStatus, MiriReport, CriticScore]:
        """Full multi-dimensional evaluation for lib+test mode."""
        # Dimension 1: Miri
        miri_report = run_miri(fixed_code, test_code, self._config)

        # Build score
        score = self._build_score(
            fixed_code, original_code, original_report, miri_report,
            mode="lib", test_code=test_code,
        )

        status = self._decide_status(miri_report, original_report, score)
        return status, miri_report, score

    def evaluate_single_file(
        self,
        fixed_code: str,
        original_code: str,
        original_report: MiriReport,
        extra_miri_flags: list[str] | None = None,
    ) -> tuple[FixStatus, MiriReport, CriticScore]:
        """Full multi-dimensional evaluation for single-file mode."""
        miri_report = run_miri_single_file(fixed_code, self._config, extra_miri_flags)

        score = self._build_score(
            fixed_code, original_code, original_report, miri_report,
            mode="single",
        )

        status = self._decide_status(miri_report, original_report, score)
        return status, miri_report, score

    def evaluate_candidate(
        self,
        candidate: FixCandidate,
        test_code: str,
        original_code: str,
        original_report: MiriReport,
    ) -> FixCandidate:
        """Evaluate a FixCandidate and update it in-place."""
        status, miri_report, score = self.evaluate(
            candidate.code, test_code, original_code, original_report,
        )
        candidate.miri_report = miri_report
        candidate.score = score
        candidate.status = status
        return candidate

    # -------------------------------------------------------------------
    # Internal scoring
    # -------------------------------------------------------------------

    def _build_score(
        self,
        fixed_code: str,
        original_code: str,
        original_report: MiriReport,
        miri_report: MiriReport,
        mode: str = "lib",
        test_code: str = "",
    ) -> CriticScore:
        score = CriticScore(miri_passed=miri_report.passed)

        # Dimension 2: Clippy static analysis
        if self._clippy:
            try:
                if mode == "single":
                    clippy_result = self._clippy.analyze_single_file(fixed_code)
                else:
                    clippy_result = self._clippy.analyze(fixed_code, test_code)
                score.clippy_warnings = clippy_result.warnings
                max_w = 20  # normalize: 20+ warnings → score 0
                score.static_score = max(0.0, 1.0 - clippy_result.warnings / max_w)
            except Exception as e:
                logger.warning("Clippy analysis failed: %s", e)
                score.static_score = 0.5
        else:
            score.static_score = 0.5

        # Dimension 3: Semantic preservation (LLM)
        if self._semantic_checker:
            try:
                score.semantic_score = self._semantic_checker.check(
                    original_code, fixed_code, original_report.error_type.value,
                )
            except Exception as e:
                logger.warning("Semantic check failed: %s", e)
                score.semantic_score = 0.5
        else:
            score.semantic_score = 0.5

        # Dimension 4: Minimal change (AST diff)
        try:
            score.minimal_change_score = compute_ast_diff_score(original_code, fixed_code)
        except Exception:
            score.minimal_change_score = 0.5

        # Bonus info: unsafe block delta
        try:
            orig_unsafe = count_unsafe_blocks(original_code)
            fixed_unsafe = count_unsafe_blocks(fixed_code)
            score.unsafe_block_delta = fixed_unsafe - orig_unsafe
        except Exception:
            pass

        return score

    def _decide_status(
        self,
        new_report: MiriReport,
        original_report: MiriReport,
        score: CriticScore,
    ) -> FixStatus:
        if new_report.passed:
            return FixStatus.MIRI_PASSED

        if "error[E" in new_report.raw_stderr:
            return FixStatus.COMPILE_ERROR

        # Score-based rejection
        if score.composite < self._config.score_threshold:
            return FixStatus.SCORE_DROPPED

        if new_report.error_type != original_report.error_type:
            return FixStatus.ERROR_TYPE_CHANGED

        return FixStatus.SAME_ERROR

    # -------------------------------------------------------------------
    # Multi-candidate selection
    # -------------------------------------------------------------------

    @staticmethod
    def select_best(candidates: list[FixCandidate]) -> FixCandidate | None:
        """Select the best candidate from evaluated candidates.

        Priority: MIRI_PASSED > highest composite score.
        """
        if not candidates:
            return None

        passed = [c for c in candidates if c.status == FixStatus.MIRI_PASSED]
        if passed:
            return max(passed, key=lambda c: c.score.composite)

        # No candidate passed Miri — pick the one with best composite
        non_dropped = [c for c in candidates if c.status != FixStatus.SCORE_DROPPED]
        if non_dropped:
            return max(non_dropped, key=lambda c: c.score.composite)

        # All dropped — return the least bad one
        return max(candidates, key=lambda c: c.score.composite)


# ---------------------------------------------------------------------------
# Backward-compatible simple critics (kept for run_single_file etc.)
# ---------------------------------------------------------------------------

class Critic:
    """Simple backward-compatible critic (Miri-only)."""

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
    """Simple backward-compatible critic for single-file mode."""

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
