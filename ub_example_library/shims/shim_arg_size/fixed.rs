fn main() {
    extern "C" {
        // Corrected: Use `std::ffi::c_int` to match the C `int` type for the `c` argument.
        fn memchr(s: *const std::ffi::c_void, c: std::ffi::c_int, n: usize) -> *mut std::ffi::c_void;
    }

    // Create a valid allocation to obtain a non-null pointer.
    // C standard library functions like `memchr` require non-null pointers
    // even when the length argument `n` is zero.
    let data = [0u8; 1];
    let ptr = data.as_ptr() as *const std::ffi::c_void;

    unsafe {
        // The second argument is correctly treated as a c_int by the ABI.
        // We pass a valid pointer instead of null to avoid Undefined Behavior.
        memchr(ptr, 0, 0);
    };
}