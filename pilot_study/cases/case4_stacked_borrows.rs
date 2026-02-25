/// Case 4: Stacked Borrows violation
/// Creating mutable and immutable references that violate aliasing rules.

pub fn increment_through_alias(x: &mut i32) -> i32 {
    let ptr = x as *mut i32;
    let ref_x = &*x; // immutable borrow
    unsafe {
        *ptr += 1; // write through raw pointer invalidates ref_x
    }
    *ref_x // UB: reading through invalidated reference
}
