"""RAG module for retrieving UB fix examples (placeholder for now)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UBExample:
    error_type: str
    buggy_code: str
    error_report: str
    fixed_code: str
    explanation: str = ""


class UBExampleLibrary:
    """Retrieves few-shot examples from the UB Example Library.

    Currently a stub — will be populated from Miri's official test suite.
    """

    def __init__(self, library_path: str | None = None):
        self._examples: list[UBExample] = []
        if library_path:
            self._load(library_path)

    def _load(self, path: str) -> None:
        # TODO: load from JSON/YAML files extracted from Miri repo
        pass

    def retrieve(self, error_type: str, k: int = 3) -> list[UBExample]:
        """Return top-k examples matching the given error type."""
        matched = [e for e in self._examples if e.error_type == error_type]
        return matched[:k]

    def add_example(self, example: UBExample) -> None:
        self._examples.append(example)

    @property
    def size(self) -> int:
        return len(self._examples)
