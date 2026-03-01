fn main() {
    // No retry needed, this fails reliably.

    let mut x = [0u8; 20];
    let x_ptr: *mut u8 = x.as_mut_ptr();
    unsafe {
        // Use write_unaligned to safely handle potentially unaligned pointers.
        // Standard dereferencing via * requires the pointer to be aligned to the type's alignment.
        std::ptr::write_unaligned(x_ptr as *mut u32, 42);
        std::ptr::write_unaligned(x_ptr.add(1) as *mut u32, 42);
    };
}