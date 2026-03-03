mod utils {
    extern "Rust" {
        pub fn miri_promise_symbolic_alignment(ptr: *const (), align: usize);
    }
}

use std::mem;

fn main() {
    let buffer = [0u32; 128];
    // Use a valid power-of-two alignment (e.g., align_of::<u32>())
    let align = mem::align_of::<u32>();

    unsafe {
        utils::miri_promise_symbolic_alignment(
            buffer.as_ptr().cast(),
            align,
        )
    };
}