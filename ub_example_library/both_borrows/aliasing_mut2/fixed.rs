use std::mem;

// Use raw pointers to allow legal aliasing and avoid the exclusivity requirements of references.
fn safe(x: *const i32, y: *mut i32) {
    unsafe {
        // Reading through a raw pointer that aliases with a mutable raw pointer is allowed.
        let _v = *x;
        // Writing through a raw pointer is allowed even if other raw pointers to the same memory exist.
        *y = 2;
    }
}

fn main() {
    let mut x = 0;
    
    // Derive raw pointers correctly using 'as' casts.
    // This avoids the Undefined Behavior caused by the exclusivity of &mut T.
    let xraw: *mut i32 = &mut x as *mut i32;
    let xshr: *const i32 = &x as *const i32;

    // Call the function directly with raw pointers.
    // This avoids the need for function pointer transmutation and ensures no invalid retagging occurs.
    safe(xshr, xraw);
}