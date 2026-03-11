"""Context Assembler — gathers all upstream information into a RepairContext."""

from __future__ import annotations

from .ast_parser import ast_summary, borrow_summary, unsafe_summary
from .error_localization import localize_error
from .knowledge_graph import build_knowledge_text
from .models import (
    FixAttempt,
    MiriReport,
    ReflectionResult,
    RepairContext,
)
from .rag import UBExample, UBExampleLibrary


class ContextAssembler:
    """Deterministic module that assembles all context for the fix loop."""

    def __init__(self, rag_library: UBExampleLibrary):
        self._rag = rag_library

    def assemble(
        self,
        source_code: str,
        test_code: str,
        miri_report: MiriReport,
        hallucinated_code: str = "",
        fix_history: list[FixAttempt] | None = None,
        reflection: ReflectionResult | None = None,
    ) -> RepairContext:
        # AST analysis
        ast_text = ast_summary(source_code)
        unsafe_text = unsafe_summary(source_code)
        borrow_text = borrow_summary(source_code)

        # Error localization
        loc = localize_error(source_code, miri_report)

        # RAG retrieval (two-stage)
        few_shots = self._rag.retrieve(
            error_type=miri_report.error_type.value,
            k=3,
            query_code=source_code,
            query_error=miri_report.raw_stderr,
        )

        # UB type knowledge
        knowledge_text = build_knowledge_text(miri_report.error_type)

        # Parse unsafe blocks into list of strings for the context
        unsafe_blocks = [b.strip() for b in unsafe_text.split("\n") if b.strip()] if unsafe_text != "(no unsafe blocks found)" else []

        return RepairContext(
            source_code=source_code,
            test_code=test_code,
            miri_report=miri_report,
            ast_summary=ast_text,
            unsafe_blocks=unsafe_blocks,
            borrow_graph=borrow_text,
            localized_error=loc,
            few_shot_examples=few_shots,
            ub_type_knowledge=knowledge_text,
            hallucinated_code=hallucinated_code,
            fix_history=fix_history or [],
            reflection=reflection,
        )

    def update_for_iteration(
        self,
        ctx: RepairContext,
        new_code: str,
        new_report: MiriReport,
        new_history: list[FixAttempt],
        reflection: ReflectionResult | None = None,
    ) -> RepairContext:
        """Update the context for the next iteration without re-running full assembly."""
        ctx.source_code = new_code
        ctx.miri_report = new_report
        ctx.fix_history = new_history
        ctx.reflection = reflection

        # Refresh AST-related fields for the updated code
        ctx.ast_summary = ast_summary(new_code)
        ctx.unsafe_blocks = [
            b.strip()
            for b in unsafe_summary(new_code).split("\n")
            if b.strip() and b.strip() != "(no unsafe blocks found)"
        ]
        ctx.borrow_graph = borrow_summary(new_code)
        ctx.localized_error = localize_error(new_code, new_report)
        ctx.ub_type_knowledge = build_knowledge_text(new_report.error_type)

        return ctx
