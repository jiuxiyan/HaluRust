use std::ffi::c_void;

fn main() {
    extern "C" {
        fn malloc(size: usize) -> *mut c_void;
        fn free(ptr: *mut c_void);
    }

    unsafe {
        let ptr = malloc(0);
        if !ptr.is_null() {
            free(ptr);
        }
    };
}