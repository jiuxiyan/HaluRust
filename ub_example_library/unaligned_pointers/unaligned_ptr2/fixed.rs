// This should fail even without validation or Stacked Borrows.

fn main() {
    // No retry needed, this fails reliably.

    let x = [2u32, 3]; // Make it big enough so we don't get an out-of-bounds error.
    let x = (x.as_ptr() as *const u8).wrapping_offset(3) as *const u32;
    // To avoid alignment violation, we use read_unaligned instead of a direct dereference.
    // This allows reading from a pointer that is not sufficiently aligned for its type.
    let _x = unsafe { x.read_unaligned() };
}