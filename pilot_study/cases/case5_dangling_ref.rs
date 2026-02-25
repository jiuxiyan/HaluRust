/// Case 5: Dangling reference via Vec reallocation
/// Push to a Vec while holding a reference to its elements.

pub fn push_and_read() -> i32 {
    let mut v = vec![1, 2, 3];
    let first = unsafe { &*v.as_ptr() }; // raw pointer to first element
    // Force reallocation
    for i in 0..100 {
        v.push(i);
    }
    *first // UB: first may now point to freed memory
}
