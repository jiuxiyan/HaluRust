fn main() {
    let data = [1_u8, 2_u8];
    let ptr1 = &data[0] as *const u8;
    let ptr2 = &data[1] as *const u8;
    unsafe {
        // Both pointers are now derived from the same allocation (the 'data' array),
        // which satisfies the safety requirements for offset_from.
        ptr1.offset_from(ptr2);
    }
}