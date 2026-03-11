"""Experience Accumulation — post-fix processing for learning and quality assurance.

Modules:
  - FixExplanationGenerator  (via agents.py)
  - RegressionTestGenerator  (via agents.py)
  - RAG Library Auto-Update
  - Fix Pattern Miner
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .agents import FixExplanationGenerator, RegressionTestGenerator
from .config import HaluRustConfig
from .llm_client import LLMClient
from .models import FixExperience, FixHistory, MiriReport
from .rag import UBExample, UBExampleLibrary

logger = logging.getLogger(__name__)


class ExperienceAccumulator:
    """Orchestrates all post-fix experience accumulation tasks."""

    def __init__(
        self,
        config: HaluRustConfig,
        llm: LLMClient,
        rag_library: UBExampleLibrary,
        library_dir: str = "",
    ):
        self._config = config
        self._explanation_gen = FixExplanationGenerator(llm)
        self._regression_gen = RegressionTestGenerator(llm)
        self._rag = rag_library
        self._library_dir = library_dir
        self._pattern_db = FixPatternMiner()

    def process_success(
        self,
        history: FixHistory,
    ) -> FixExperience | None:
        """Run all post-fix tasks after a successful repair."""
        if not history.succeeded:
            return None

        final_code = history.final_code
        if not final_code:
            return None

        original_code = history.original_code
        error_type = history.original_report.error_type.value
        error_message = history.original_report.error_message

        # 1. Generate explanation
        logger.info("Generating fix explanation...")
        explanation = self._explanation_gen.explain(
            original_code=original_code,
            fixed_code=final_code,
            error_type=error_type,
            error_message=error_message,
        )

        # 2. Generate regression tests
        logger.info("Generating regression tests...")
        regression_tests = self._regression_gen.generate(
            original_code=original_code,
            fixed_code=final_code,
            error_type=error_type,
            explanation=explanation,
        )

        # 3. Determine fix strategy from the successful attempt
        fix_strategy = ""
        for attempt in history.attempts:
            if attempt.status.value == "miri_passed":
                fix_strategy = attempt.plan.strategy
                break

        # 4. Build the experience record
        experience = FixExperience(
            original_code=original_code,
            error_report=history.original_report.raw_stderr,
            error_type=error_type,
            fixed_code=final_code,
            explanation=explanation,
            fix_strategy=fix_strategy,
            iterations_needed=len(history.attempts),
            score=history.attempts[-1].score.composite if history.attempts else 0.0,
        )

        # 5. Auto-update RAG library
        self._update_rag(experience)

        # 6. Record fix pattern
        self._pattern_db.record(error_type, fix_strategy, success=True)
        for attempt in history.attempts:
            if attempt.status.value != "miri_passed":
                self._pattern_db.record(error_type, attempt.plan.strategy, success=False)

        return experience

    def _update_rag(self, experience: FixExperience) -> None:
        """Add the successful fix to the RAG library."""
        example = UBExample(
            error_type=experience.error_type,
            buggy_code=experience.original_code,
            error_report=experience.error_report,
            fixed_code=experience.fixed_code,
            explanation=experience.explanation,
            category=experience.category or "auto_learned",
            name=f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            fix_strategy=experience.fix_strategy,
        )

        # Add to in-memory library
        self._rag.add_example(example)
        logger.info("Added new example to RAG library (in-memory)")

        # Persist to disk if library_dir is available
        if self._library_dir:
            try:
                self._rag.save_new_example(example, self._library_dir)
                logger.info("Persisted new example to disk: %s", self._library_dir)
            except Exception as e:
                logger.warning("Failed to persist example: %s", e)

    def get_pattern_stats(self) -> dict:
        return self._pattern_db.get_stats()


class FixPatternMiner:
    """Tracks fix strategy success/failure rates across runs."""

    def __init__(self, stats_file: str | None = None):
        # stats[error_type][strategy] = {"success": N, "failure": N}
        self._stats: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"success": 0, "failure": 0})
        )
        self._stats_file = stats_file
        if stats_file:
            self._load(stats_file)

    def record(self, error_type: str, strategy: str, success: bool) -> None:
        if not strategy:
            return
        key = strategy[:120]  # truncate long strategies
        if success:
            self._stats[error_type][key]["success"] += 1
        else:
            self._stats[error_type][key]["failure"] += 1

        if self._stats_file:
            self._save()

    def get_best_strategy(self, error_type: str) -> str | None:
        """Return the strategy with the highest success rate for this error type."""
        strategies = self._stats.get(error_type, {})
        if not strategies:
            return None
        best = None
        best_rate = -1.0
        for strat, counts in strategies.items():
            total = counts["success"] + counts["failure"]
            if total == 0:
                continue
            rate = counts["success"] / total
            if rate > best_rate:
                best_rate = rate
                best = strat
        return best

    def get_stats(self) -> dict:
        """Return all stats as a plain dict."""
        return {
            error_type: {
                strat: {
                    **counts,
                    "rate": counts["success"] / max(1, counts["success"] + counts["failure"]),
                }
                for strat, counts in strategies.items()
            }
            for error_type, strategies in self._stats.items()
        }

    def _load(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            try:
                data = json.loads(p.read_text())
                for etype, strategies in data.items():
                    for strat, counts in strategies.items():
                        self._stats[etype][strat] = counts
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        if not self._stats_file:
            return
        try:
            Path(self._stats_file).write_text(json.dumps(dict(self._stats), indent=2))
        except OSError:
            pass
