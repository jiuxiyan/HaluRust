"""Parse Rust source code into AST using tree-sitter."""

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
