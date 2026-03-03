"""RAG module for retrieving UB fix examples from the example library."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UBExample:
    error_type: str
    buggy_code: str
    error_report: str
    fixed_code: str
    explanation: str = ""
    category: str = ""
    name: str = ""


# Mapping from Miri error keywords to our canonical error_type values
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
    """Retrieves few-shot examples from the UB Example Library.

    Loads from ub_example_library/index.json which contains pre-computed
    (buggy_code, error_report, fixed_code) triples organized by UB category.
    """

    def __init__(self, library_path: str | None = None):
        self._examples: list[UBExample] = []
        self._by_error_type: dict[str, list[UBExample]] = {}
        self._by_category: dict[str, list[UBExample]] = {}
        if library_path:
            self._load(library_path)

    def _load(self, path: str) -> None:
        """Load examples from index.json or by scanning the library directory."""
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
            ))

    def _load_from_directory(self, lib_dir: Path) -> None:
        """Scan category/example/ subdirectories for metadata.json + code files."""
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

    def retrieve(self, error_type: str, k: int = 3) -> list[UBExample]:
        """Return top-k examples matching the given error type.

        Uses fuzzy matching: if exact error_type match is insufficient,
        falls back to category-based and alias-based matching.
        """
        # Exact match first
        exact = self._by_error_type.get(error_type, [])
        if len(exact) >= k:
            return exact[:k]

        results = list(exact)

        # Try alias matching
        for canonical, aliases in _ERROR_TYPE_ALIASES.items():
            if error_type in aliases or error_type == canonical:
                for alias_type in aliases:
                    for ex in self._by_error_type.get(alias_type, []):
                        if ex not in results:
                            results.append(ex)
                            if len(results) >= k:
                                return results[:k]

        # Fall back to category matching based on error_type keywords
        if len(results) < k:
            for cat, examples in self._by_category.items():
                if error_type.replace("_", "") in cat.replace("_", ""):
                    for ex in examples:
                        if ex not in results:
                            results.append(ex)
                            if len(results) >= k:
                                return results[:k]

        return results[:k]

    def add_example(self, example: UBExample) -> None:
        self._examples.append(example)
        self._by_error_type.setdefault(example.error_type, []).append(example)
        if example.category:
            self._by_category.setdefault(example.category, []).append(example)

    @property
    def size(self) -> int:
        return len(self._examples)

    @property
    def categories(self) -> list[str]:
        return sorted(self._by_category.keys())

    @property
    def error_types(self) -> list[str]:
        return sorted(self._by_error_type.keys())
