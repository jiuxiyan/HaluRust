fn main() {
    fn f(_: *const [i32]) {}

    let val = 42;
    let ptr: *const i32 = &val;

    // Create a slice pointer of length 1 from the thin pointer
    let slice_ptr: *const [i32] = std::ptr::slice_from_raw_parts(ptr, 1);

    // Call the function with the correct type
    f(slice_ptr);
}