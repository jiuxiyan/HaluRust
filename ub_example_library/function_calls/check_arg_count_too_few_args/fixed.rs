fn main() {
    extern "C" {
        fn malloc(size: usize) -> *mut std::ffi::c_void;
        fn free(ptr: *mut std::ffi::c_void);
    }

    unsafe {
        let ptr = malloc(1024);
        if !ptr.is_null() {
            free(ptr);
        }
    };
}