// With the symbolic alignment check, even with intptrcast and without
// validation, we want to be *sure* to catch bugs that arise from pointers being
// insufficiently aligned. The only way to achieve that is not to let programs
// exploit integer information for alignment, so here we test that this is
// indeed the case.
//
// See https://github.com/rust-lang/miri/issues/1074.
fn main() {
    let x = &mut [0u8; 3];
    let base_addr = x as *mut _ as usize;
    // Manually make sure the pointer is properly aligned.
    let base_addr_aligned = if base_addr % 2 == 0 { base_addr } else { base_addr + 1 };
    let u16_ptr = base_addr_aligned as *mut u16;
    unsafe {
        // Use write_unaligned to avoid Undefined Behavior from potential misalignment.
        // Even if the address is numerically even, the underlying allocation for [u8; 3]
        // only guarantees an alignment of 1.
        std::ptr::write_unaligned(u16_ptr, 2);
    }
    println!("{:?}", x);
}