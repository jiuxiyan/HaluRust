static ARRAY: [u8; 2] = [0, 1];

fn main() {
    // Derive the pointer from the whole array, not just the first element.
    // This gives the pointer provenance over the entire range of the array.
    let ptr_to_start = ARRAY.as_ptr();
    
    // Now accessing the 2nd element via pointer arithmetic is valid.
    let _val = unsafe { *ptr_to_start.add(1) };
    
    assert_eq!(_val, 1);
}