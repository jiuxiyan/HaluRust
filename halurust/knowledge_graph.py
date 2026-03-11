"""UB Type Knowledge Graph — hierarchical relationships and common fix patterns."""

from __future__ import annotations

from .models import MiriErrorType


# ---------------------------------------------------------------------------
# Hierarchy: each UB type belongs to a family, families share fix strategies
# ---------------------------------------------------------------------------

UB_FAMILY: dict[str, list[MiriErrorType]] = {
    "pointer_validity": [
        MiriErrorType.USE_AFTER_FREE,
        MiriErrorType.DANGLING_REFERENCE,
        MiriErrorType.OUT_OF_BOUNDS,
        MiriErrorType.INVALID_DEREF,
    ],
    "borrow_model": [
        MiriErrorType.STACKED_BORROWS,
        MiriErrorType.TREE_BORROWS,
    ],
    "memory_state": [
        MiriErrorType.UNINITIALIZED,
        MiriErrorType.INVALID_ALIGNMENT,
    ],
    "concurrency": [
        MiriErrorType.DATA_RACE,
    ],
    "provenance": [
        MiriErrorType.INT_TO_PTR_CAST,
    ],
    "resource": [
        MiriErrorType.MEMORY_LEAK,
    ],
}

_TYPE_TO_FAMILY: dict[MiriErrorType, str] = {}
for _fam, _types in UB_FAMILY.items():
    for _t in _types:
        _TYPE_TO_FAMILY[_t] = _fam


# Pairwise similarity: 1.0 = same, 0.8 = same family, 0.3 = different family
def type_similarity(a: MiriErrorType, b: MiriErrorType) -> float:
    if a == b:
        return 1.0
    fa = _TYPE_TO_FAMILY.get(a)
    fb = _TYPE_TO_FAMILY.get(b)
    if fa and fb and fa == fb:
        return 0.8
    return 0.3


def get_family(error_type: MiriErrorType) -> str:
    return _TYPE_TO_FAMILY.get(error_type, "unknown")


def get_sibling_types(error_type: MiriErrorType) -> list[MiriErrorType]:
    """Return other UB types in the same family."""
    family = get_family(error_type)
    return [t for t in UB_FAMILY.get(family, []) if t != error_type]


def is_same_family(a: MiriErrorType, b: MiriErrorType) -> bool:
    return get_family(a) == get_family(b)


# ---------------------------------------------------------------------------
# Common fix patterns per UB type
# ---------------------------------------------------------------------------

FIX_PATTERNS: dict[MiriErrorType, list[str]] = {
    MiriErrorType.USE_AFTER_FREE: [
        "Replace raw pointer with owned type (Box<T>, Rc<T>)",
        "Ensure the referenced data outlives the pointer by restructuring lifetimes",
        "Use arena allocation to tie pointer lifetime to a known scope",
        "Replace pointer-based access with index-based access into a Vec",
    ],
    MiriErrorType.DANGLING_REFERENCE: [
        "Avoid returning references to stack-local data",
        "Use owned types instead of borrowed references where lifetime is unclear",
        "Restructure code so the borrow does not outlive the referent",
        "Use Rc<T>/Arc<T> for shared ownership across scopes",
    ],
    MiriErrorType.OUT_OF_BOUNDS: [
        "Add bounds checking before pointer arithmetic or slice indexing",
        "Replace raw pointer offset with safe slice operations",
        "Use .get() instead of direct indexing to avoid panics",
        "Recalculate buffer sizes to ensure sufficient allocation",
    ],
    MiriErrorType.INVALID_DEREF: [
        "Check for null before dereferencing raw pointers",
        "Replace raw pointer with Option<&T> or Option<Box<T>>",
        "Use NonNull<T> to guarantee non-null raw pointers",
    ],
    MiriErrorType.STACKED_BORROWS: [
        "Avoid creating mutable aliases — ensure only one &mut at a time",
        "Use UnsafeCell<T> or Cell<T> for interior mutability patterns",
        "Re-derive the mutable pointer from the original source before use",
        "Restructure code to avoid interleaving reads/writes through aliased pointers",
    ],
    MiriErrorType.TREE_BORROWS: [
        "Ensure foreign reads do not invalidate active mutable borrows",
        "Restructure borrow tree so child borrows do not outlive parent permissions",
        "Use raw pointers consistently when mixed-access patterns are required",
        "Wrap shared state in UnsafeCell to opt out of borrow restrictions",
    ],
    MiriErrorType.UNINITIALIZED: [
        "Initialize memory with MaybeUninit<T>::zeroed() or explicit writes before read",
        "Use safe constructors instead of alloc + manual init",
        "Replace assume_init() with proper initialization guards",
        "Use Vec::with_capacity + push instead of set_len on uninitialized buffer",
    ],
    MiriErrorType.INVALID_ALIGNMENT: [
        "Use #[repr(align(N))] to ensure proper struct alignment",
        "Replace unaligned pointer casts with read_unaligned/write_unaligned",
        "Allocate with Layout::from_size_align to guarantee alignment",
    ],
    MiriErrorType.DATA_RACE: [
        "Wrap shared state in Mutex<T> or RwLock<T>",
        "Use atomic types (AtomicBool, AtomicUsize, etc.) for lock-free access",
        "Use channels (mpsc) instead of shared mutable state",
        "Add proper synchronization barriers (fences, happens-before ordering)",
    ],
    MiriErrorType.INT_TO_PTR_CAST: [
        "Use strict provenance APIs: .with_addr(), .map_addr()",
        "Expose pointers via ptr::from_exposed_addr instead of direct casts",
        "Avoid round-tripping pointers through integers when possible",
    ],
    MiriErrorType.MEMORY_LEAK: [
        "Ensure all heap allocations are freed (drop Box, Vec, etc.)",
        "Break reference cycles in Rc<T> using Weak<T>",
        "Use RAII patterns — tie resource cleanup to scope exit",
        "Replace manual allocation with owning containers",
    ],
}


# ---------------------------------------------------------------------------
# Severity ranking (higher = more dangerous for the program)
# ---------------------------------------------------------------------------

UB_SEVERITY: dict[MiriErrorType, int] = {
    MiriErrorType.USE_AFTER_FREE: 10,
    MiriErrorType.DATA_RACE: 9,
    MiriErrorType.INVALID_DEREF: 9,
    MiriErrorType.OUT_OF_BOUNDS: 8,
    MiriErrorType.DANGLING_REFERENCE: 8,
    MiriErrorType.UNINITIALIZED: 7,
    MiriErrorType.STACKED_BORROWS: 6,
    MiriErrorType.TREE_BORROWS: 6,
    MiriErrorType.INVALID_ALIGNMENT: 5,
    MiriErrorType.INT_TO_PTR_CAST: 4,
    MiriErrorType.MEMORY_LEAK: 3,
    MiriErrorType.UNKNOWN: 1,
}


def get_severity(error_type: MiriErrorType) -> int:
    return UB_SEVERITY.get(error_type, 1)


def get_fix_patterns(error_type: MiriErrorType) -> list[str]:
    patterns = FIX_PATTERNS.get(error_type, [])
    if not patterns:
        for sibling in get_sibling_types(error_type):
            patterns.extend(FIX_PATTERNS.get(sibling, []))
    return patterns


def build_knowledge_text(error_type: MiriErrorType) -> str:
    """Build a text block describing the UB type for LLM context."""
    family = get_family(error_type)
    severity = get_severity(error_type)
    siblings = get_sibling_types(error_type)
    patterns = get_fix_patterns(error_type)

    lines = [
        f"## UB Type Knowledge: {error_type.value}",
        f"Family: {family}",
        f"Severity: {severity}/10",
    ]
    if siblings:
        lines.append(f"Related types: {', '.join(s.value for s in siblings)}")
    if patterns:
        lines.append("\nCommon fix patterns:")
        for i, p in enumerate(patterns, 1):
            lines.append(f"  {i}. {p}")
    return "\n".join(lines)
