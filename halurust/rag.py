"""RAG module for retrieving UB fix examples from the example library.

Enhanced with optional semantic embedding retrieval and auto-update capability.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from difflib import SequenceMatcher

from .knowledge_graph import get_sibling_types, type_similarity
from .models import MiriErrorType

logger = logging.getLogger(__name__)


@dataclass
class UBExample:
    error_type: str
    buggy_code: str
    error_report: str
    fixed_code: str
    explanation: str = ""
    category: str = ""
    name: str = ""
    fix_strategy: str = ""


# Mapping from Miri error keywords to canonical error_type values
_ERROR_TYPE_ALIASES: dict[str, list[str]] = {
    "use_after_free": ["use_after_free", "dangling"],
    "out_of_bounds": ["out_of_bounds"],
    "invalid_deref": ["invalid_deref", "null"],
    "uninitialized_memory": ["uninitialized_memory", "uninit"],
    "data_race": ["data_race"],
    "invalid_alignment": ["invalid_alignment", "alignment", "unaligned"],
    "dangling_reference": ["dangling_reference", "dangling"],
    "stacked_borrows": ["stacked_borrows"],
    "tree_borrows": ["tree_borrows"],
    "int_to_ptr_cast": ["int_to_ptr_cast"],
    "memory_leak": ["memory_leak", "memleak"],
    "unknown": ["unknown"],
}


class UBExampleLibrary:
    """Retrieves few-shot examples using a two-stage approach:
    Stage 1: Filter by error_type (exact → alias → family)
    Stage 2: Rank by textual similarity of error_report + buggy_code
    """

    def __init__(self, library_path: str | None = None):
        self._examples: list[UBExample] = []
        self._by_error_type: dict[str, list[UBExample]] = {}
        self._by_category: dict[str, list[UBExample]] = {}
        self._embeddings: dict[int, list[float]] = {}  # index → embedding vector
        self._embed_fn = None  # lazy-loaded embedding function
        if library_path:
            self._load(library_path)

    # -------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------

    def _load(self, path: str) -> None:
        lib_path = Path(path)
        if lib_path.is_file() and lib_path.name == "index.json":
            self._load_from_index(lib_path)
        elif lib_path.is_dir():
            index_file = lib_path / "index.json"
            if index_file.exists():
                self._load_from_index(index_file)
            else:
                self._load_from_directory(lib_path)
        self._build_indices()

    def _load_from_index(self, index_path: Path) -> None:
        data = json.loads(index_path.read_text())
        for entry in data.get("examples", []):
            self._examples.append(UBExample(
                error_type=entry.get("error_type", "unknown"),
                buggy_code=entry.get("buggy_code", ""),
                error_report=entry.get("error_report", ""),
                fixed_code=entry.get("fixed_code", ""),
                explanation=entry.get("error_message", ""),
                category=entry.get("category", ""),
                name=entry.get("name", ""),
                fix_strategy=entry.get("fix_strategy", ""),
            ))

    def _load_from_directory(self, lib_dir: Path) -> None:
        for meta_file in sorted(lib_dir.rglob("metadata.json")):
            example_dir = meta_file.parent
            try:
                metadata = json.loads(meta_file.read_text())
                original = (example_dir / "original.rs").read_text() if (example_dir / "original.rs").exists() else ""
                fixed = (example_dir / "fixed.rs").read_text() if (example_dir / "fixed.rs").exists() else ""
                stderr = (example_dir / "miri_stderr.txt").read_text() if (example_dir / "miri_stderr.txt").exists() else ""
                self._examples.append(UBExample(
                    error_type=metadata.get("error_type", "unknown"),
                    buggy_code=original,
                    error_report=stderr,
                    fixed_code=fixed,
                    explanation=metadata.get("error_message", ""),
                    category=metadata.get("category", ""),
                    name=metadata.get("name", ""),
                    fix_strategy=metadata.get("fix_strategy", ""),
                ))
            except (json.JSONDecodeError, OSError):
                continue

    def _build_indices(self) -> None:
        self._by_error_type.clear()
        self._by_category.clear()
        for ex in self._examples:
            self._by_error_type.setdefault(ex.error_type, []).append(ex)
            if ex.category:
                self._by_category.setdefault(ex.category, []).append(ex)

    # -------------------------------------------------------------------
    # Two-stage retrieval: type-filter → similarity-rank
    # -------------------------------------------------------------------

    def retrieve(self, error_type: str, k: int = 3,
                 query_code: str = "", query_error: str = "") -> list[UBExample]:
        """Return top-k examples. Uses type filtering then similarity ranking."""
        candidates = self._gather_candidates(error_type)

        if not candidates:
            return []

        if query_code or query_error:
            candidates = self._rank_by_similarity(candidates, query_code, query_error)

        return candidates[:k]

    def _gather_candidates(self, error_type: str) -> list[UBExample]:
        """Stage 1: Gather candidates by type (exact → alias → family)."""
        # Exact match
        results = list(self._by_error_type.get(error_type, []))

        # Alias matching
        for canonical, aliases in _ERROR_TYPE_ALIASES.items():
            if error_type in aliases or error_type == canonical:
                for alias_type in aliases:
                    for ex in self._by_error_type.get(alias_type, []):
                        if ex not in results:
                            results.append(ex)

        # Family matching via knowledge graph
        try:
            miri_type = MiriErrorType(error_type)
            for sibling in get_sibling_types(miri_type):
                for ex in self._by_error_type.get(sibling.value, []):
                    if ex not in results:
                        results.append(ex)
        except ValueError:
            pass

        # Category fallback
        for cat, examples in self._by_category.items():
            if error_type.replace("_", "") in cat.replace("_", ""):
                for ex in examples:
                    if ex not in results:
                        results.append(ex)

        return results

    def _rank_by_similarity(
        self, candidates: list[UBExample], query_code: str, query_error: str
    ) -> list[UBExample]:
        """Stage 2: Rank candidates by textual similarity to the query."""
        scored: list[tuple[float, UBExample]] = []
        for ex in candidates:
            code_sim = _text_similarity(query_code, ex.buggy_code) if query_code else 0.0
            error_sim = _text_similarity(query_error, ex.error_report) if query_error else 0.0
            combined = 0.4 * code_sim + 0.6 * error_sim
            scored.append((combined, ex))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored]

    # -------------------------------------------------------------------
    # Auto-update: add successful fixes back to the library
    # -------------------------------------------------------------------

    def add_example(self, example: UBExample) -> None:
        self._examples.append(example)
        self._by_error_type.setdefault(example.error_type, []).append(example)
        if example.category:
            self._by_category.setdefault(example.category, []).append(example)

    def save_new_example(self, example: UBExample, library_dir: str) -> None:
        """Persist a new example to disk under the library directory."""
        lib_path = Path(library_dir)
        safe_name = example.name.replace("/", "_").replace(" ", "_") or "auto_added"
        category = example.category or "auto"
        example_dir = lib_path / category / safe_name
        example_dir.mkdir(parents=True, exist_ok=True)

        (example_dir / "original.rs").write_text(example.buggy_code)
        (example_dir / "fixed.rs").write_text(example.fixed_code)
        (example_dir / "miri_stderr.txt").write_text(example.error_report)
        metadata = {
            "name": example.name,
            "category": example.category,
            "error_type": example.error_type,
            "error_message": example.explanation,
            "fix_strategy": example.fix_strategy,
        }
        (example_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        logger.info("Saved new example to %s", example_dir)

    # -------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._examples)

    @property
    def categories(self) -> list[str]:
        return sorted(self._by_category.keys())

    @property
    def error_types(self) -> list[str]:
        return sorted(self._by_error_type.keys())


# ---------------------------------------------------------------------------
# Similarity utilities
# ---------------------------------------------------------------------------

def _text_similarity(a: str, b: str) -> float:
    """Quick textual similarity using SequenceMatcher (no external deps)."""
    if not a or not b:
        return 0.0
    # Truncate to avoid slow comparisons on very long texts
    a_trunc = a[:2000]
    b_trunc = b[:2000]
    return SequenceMatcher(None, a_trunc, b_trunc).ratio()
