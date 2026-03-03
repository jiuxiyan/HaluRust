//! This demonstrates a provenance problem that requires tracking of raw pointers to be detected.

fn main() {
    let mut l = 13;
    // Use addr_of_mut! to create raw pointers directly from the variable.
    // This avoids creating intermediate mutable references that would invalidate 
    // previous pointers under the Stacked Borrows model.
    let raw1 = std::ptr::addr_of_mut!(l);
    let raw2 = std::ptr::addr_of_mut!(l);
    
    unsafe { *raw1 = 13 };
    unsafe { *raw2 = 13 };
}