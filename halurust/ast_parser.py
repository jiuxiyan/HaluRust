"""Parse Rust source code into AST using tree-sitter.

Enhanced with unsafe block extraction, borrow relation analysis, and AST diff.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import tree_sitter_rust as tsrust
from tree_sitter import Language, Parser


RUST_LANGUAGE = Language(tsrust.language())


@dataclass
class ASTNode:
    type: str
    text: str
    start_line: int
    end_line: int
    children: list["ASTNode"] = field(default_factory=list)


def parse_rust(source: str) -> ASTNode:
    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))
    return _convert_node(tree.root_node, source)


def _convert_node(node, source: str) -> ASTNode:
    children = [_convert_node(c, source) for c in node.children if c.is_named]
    return ASTNode(
        type=node.type,
        text=node.text.decode("utf8") if node.text else "",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        children=children,
    )


# ---------------------------------------------------------------------------
# Function-level extraction (original)
# ---------------------------------------------------------------------------

def get_function_nodes(source: str) -> list[ASTNode]:
    root = parse_rust(source)
    return _collect_functions(root)


def _collect_functions(node: ASTNode) -> list[ASTNode]:
    result = []
    if node.type in ("function_item", "impl_item"):
        result.append(node)
    for child in node.children:
        result.extend(_collect_functions(child))
    return result


def ast_summary(source: str) -> str:
    """Generate a compact textual summary of the AST for LLM context."""
    functions = get_function_nodes(source)
    lines = []
    for fn in functions:
        first_line = fn.text.split("\n")[0]
        lines.append(f"[L{fn.start_line}-L{fn.end_line}] {fn.type}: {first_line}")
    return "\n".join(lines) if lines else "(no function-level nodes found)"


# ---------------------------------------------------------------------------
# Unsafe block extraction (new)
# ---------------------------------------------------------------------------

@dataclass
class UnsafeBlock:
    start_line: int
    end_line: int
    text: str
    parent_function: str = ""


def extract_unsafe_blocks(source: str) -> list[UnsafeBlock]:
    """Extract all unsafe blocks with their parent function context."""
    root = parse_rust(source)
    blocks: list[UnsafeBlock] = []
    _find_unsafe_blocks(root, parent_fn="<top-level>", results=blocks)
    return blocks


def _find_unsafe_blocks(
    node: ASTNode, parent_fn: str, results: list[UnsafeBlock]
) -> None:
    current_fn = parent_fn
    if node.type == "function_item":
        first_line = node.text.split("\n")[0].strip()
        current_fn = first_line

    if node.type == "unsafe_block":
        results.append(UnsafeBlock(
            start_line=node.start_line,
            end_line=node.end_line,
            text=node.text,
            parent_function=current_fn,
        ))

    for child in node.children:
        _find_unsafe_blocks(child, current_fn, results)


def unsafe_summary(source: str) -> str:
    """Build a textual summary of all unsafe blocks."""
    blocks = extract_unsafe_blocks(source)
    if not blocks:
        return "(no unsafe blocks found)"
    lines = []
    for b in blocks:
        lines.append(f"[L{b.start_line}-L{b.end_line}] unsafe in `{b.parent_function}`")
        preview = b.text.split("\n")
        for pl in preview[:5]:
            lines.append(f"    {pl}")
        if len(preview) > 5:
            lines.append(f"    ... ({len(preview) - 5} more lines)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Borrow / reference relation extraction (new)
# ---------------------------------------------------------------------------

@dataclass
class BorrowRelation:
    variable: str
    borrow_type: str  # "shared_ref", "mut_ref", "raw_ptr", "raw_mut_ptr"
    line: int
    source_text: str


def extract_borrow_relations(source: str) -> list[BorrowRelation]:
    """Extract reference/pointer operations from the AST."""
    root = parse_rust(source)
    relations: list[BorrowRelation] = []
    _find_borrows(root, relations)
    return relations


def _find_borrows(node: ASTNode, results: list[BorrowRelation]) -> None:
    if node.type == "reference_expression":
        is_mut = any(c.type == "mutable_specifier" for c in node.children)
        btype = "mut_ref" if is_mut else "shared_ref"
        results.append(BorrowRelation(
            variable=node.text,
            borrow_type=btype,
            line=node.start_line,
            source_text=node.text,
        ))

    if node.type == "type_cast_expression" and "*const" in node.text:
        results.append(BorrowRelation(
            variable=node.text,
            borrow_type="raw_ptr",
            line=node.start_line,
            source_text=node.text,
        ))
    elif node.type == "type_cast_expression" and "*mut" in node.text:
        results.append(BorrowRelation(
            variable=node.text,
            borrow_type="raw_mut_ptr",
            line=node.start_line,
            source_text=node.text,
        ))

    for child in node.children:
        _find_borrows(child, results)


def borrow_summary(source: str) -> str:
    """Build a textual summary of borrow/reference relations."""
    relations = extract_borrow_relations(source)
    if not relations:
        return "(no borrow relations detected)"
    lines = []
    for r in relations:
        preview = r.source_text.replace("\n", " ")[:80]
        lines.append(f"  L{r.line} [{r.borrow_type}] {preview}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# AST Diff — compute structural change between two versions (new)
# ---------------------------------------------------------------------------

def count_named_nodes(node: ASTNode) -> int:
    """Count all named nodes in the tree (for minimal-change scoring)."""
    return 1 + sum(count_named_nodes(c) for c in node.children)


def _collect_node_signatures(node: ASTNode, depth: int = 0) -> list[str]:
    """Flatten tree into a list of (type, start, end) signatures."""
    sig = f"{depth}:{node.type}:{node.start_line}:{node.end_line}"
    result = [sig]
    for c in node.children:
        result.extend(_collect_node_signatures(c, depth + 1))
    return result


def compute_ast_diff_score(original: str, fixed: str) -> float:
    """Compute a 0~1 score where 1.0 = identical, 0.0 = completely different.

    Uses a simple set-overlap metric on node signatures.
    """
    try:
        root_a = parse_rust(original)
        root_b = parse_rust(fixed)
    except Exception:
        return 0.5  # fallback if parsing fails

    sigs_a = set(_collect_node_signatures(root_a))
    sigs_b = set(_collect_node_signatures(root_b))

    if not sigs_a and not sigs_b:
        return 1.0
    union = len(sigs_a | sigs_b)
    if union == 0:
        return 1.0
    intersection = len(sigs_a & sigs_b)
    return intersection / union


def count_unsafe_blocks(source: str) -> int:
    return len(extract_unsafe_blocks(source))
