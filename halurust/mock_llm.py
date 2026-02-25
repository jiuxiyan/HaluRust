"""Mock LLM client for dry-run / demo purposes.

Provides hand-crafted fixes for the pilot study cases so the full pipeline
can be exercised without an actual API key.
"""

from __future__ import annotations

from .config import HaluRustConfig


MOCK_FIXES = {
    "use_after_free": {
        "plan": """\
## Analysis
The function `get_value` creates a Box, takes a raw pointer to its contents,
drops the Box (freeing the heap memory), then dereferences the dangling pointer.

## Root Cause
The Box is dropped at the end of the inner scope, but the raw pointer `ptr` is
used after the memory has been freed.

## Fix Strategy
Keep the Box alive until after the pointer is dereferenced, or avoid raw pointers entirely.

## Steps
1. Remove the inner scope so the Box lives until the end of the function
2. Return the value before the Box is dropped
""",
        "code": """\
pub fn get_value() -> i32 {
    let val = Box::new(42);
    *val
}""",
    },
    "out_of_bounds": {
        "plan": """\
## Analysis
The function `sum_array` iterates with `0..=data.len()` which is inclusive of `data.len()`,
causing an off-by-one out-of-bounds read via raw pointer arithmetic.

## Root Cause
The range `0..=data.len()` includes `data.len()` as the last index, but valid indices are
`0..data.len()`. The raw pointer `ptr.add(data.len())` reads one element past the end.

## Fix Strategy
Change the range from `0..=data.len()` to `0..data.len()` to avoid reading past the end.

## Steps
1. Fix the loop range from inclusive `..=` to exclusive `..`
""",
        "code": """\
pub fn sum_array(data: &[i32]) -> i32 {
    let ptr = data.as_ptr();
    let mut sum = 0i32;
    for i in 0..data.len() {
        sum += unsafe { *ptr.add(i) };
    }
    sum
}""",
    },
    "uninitialized": {
        "plan": """\
## Analysis
The function creates a partially-initialized array using MaybeUninit, initializes only
3 of 5 elements, then transmutes the whole array to [i32; 5], reading uninitialized memory.

## Root Cause
Only indices 0..3 are initialized, but all 5 elements are treated as initialized via transmute.

## Fix Strategy
Initialize all 5 elements before transmuting, or change the design to only use initialized data.

## Steps
1. Initialize all 5 elements in the loop (change range from 0..3 to 0..5)
2. Use appropriate values for the additional elements (e.g., 0)
""",
        "code": """\
use std::mem::MaybeUninit;

pub fn create_array() -> [i32; 5] {
    let mut arr: [MaybeUninit<i32>; 5] = [MaybeUninit::uninit(); 5];

    for i in 0..5 {
        if i < 3 {
            arr[i] = MaybeUninit::new(i as i32 * 10);
        } else {
            arr[i] = MaybeUninit::new(0);
        }
    }

    unsafe { std::mem::transmute(arr) }
}""",
    },
    "stacked_borrows": {
        "plan": """\
## Analysis
The function creates a raw mutable pointer from `x`, then creates an immutable reference `ref_x`.
It writes through the raw pointer, which invalidates `ref_x` under Stacked Borrows rules,
then reads through the invalidated `ref_x`.

## Root Cause
Writing through `ptr` after creating `ref_x` pops the immutable borrow from the borrow stack,
making the subsequent read through `ref_x` undefined behavior.

## Fix Strategy
Restructure to avoid aliasing: perform the write through the raw pointer, then read
from the original mutable reference instead of through an invalidated shared reference.

## Steps
1. Remove the immutable reference that aliases the mutable pointer
2. Read the value after the write using the original mutable reference
""",
        "code": """\
pub fn increment_through_alias(x: &mut i32) -> i32 {
    *x += 1;
    *x
}""",
    },
    "dangling_reference": {
        "plan": """\
## Analysis
A raw pointer to the first element of a Vec is created. Then 100 elements are pushed,
which forces reallocation. The old pointer now points to freed memory.

## Root Cause
Vec reallocation moves data to a new heap location, invalidating all existing pointers.

## Fix Strategy
Save the value before the reallocation occurs, or access it after the push operations.

## Steps
1. Read the first element's value before pushing (while the pointer is still valid)
2. Return the saved value
""",
        "code": """\
pub fn push_and_read() -> i32 {
    let mut v = vec![1, 2, 3];
    let first = v[0];
    for i in 0..100 {
        v.push(i);
    }
    first
}""",
    },
}


FUNCTION_TO_UB_TYPE = {
    "get_value": "use_after_free",
    "sum_array": "out_of_bounds",
    "create_array": "uninitialized",
    "increment_through_alias": "stacked_borrows",
    "push_and_read": "dangling_reference",
}

KEYWORD_TO_UB_TYPE = {
    "has been freed": "use_after_free",
    "dangling": "use_after_free",
    "out-of-bounds": "out_of_bounds",
    "beyond the end": "out_of_bounds",
    "uninitialized": "uninitialized",
    "not initialized": "uninitialized",
    "Stacked Borrows": "stacked_borrows",
    "reborrow": "stacked_borrows",
    "realloc": "dangling_reference",
}


class MockLLMClient:
    """Returns pre-written responses for known UB patterns."""

    def __init__(self, config: HaluRustConfig):
        self._model = config.model

    def _detect_ub_type(self, text: str) -> str | None:
        for func_name, ub_type in FUNCTION_TO_UB_TYPE.items():
            if func_name in text:
                return ub_type
        for keyword, ub_type in KEYWORD_TO_UB_TYPE.items():
            if keyword in text:
                return ub_type
        return None

    def chat(self, system: str, user: str, temperature: float | None = None) -> str:
        ub_type = self._detect_ub_type(user)
        if ub_type and ub_type in MOCK_FIXES:
            fix_data = MOCK_FIXES[ub_type]
            is_plan = "plan" in system.lower() and "repair" not in system.lower()
            if is_plan:
                return fix_data["plan"]
            return f"```rust\n{fix_data['code']}\n```"

        first_fix = list(MOCK_FIXES.values())[0]
        if "plan" in system.lower():
            return first_fix["plan"]
        return f"```rust\n{first_fix['code']}\n```"

    def chat_with_history(
        self, system: str, messages: list, temperature: float | None = None
    ) -> str:
        user_msg = messages[-1]["content"] if messages else ""
        return self.chat(system, user_msg, temperature)
