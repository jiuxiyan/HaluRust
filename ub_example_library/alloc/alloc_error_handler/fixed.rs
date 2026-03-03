#![feature(allocator_api)]

use std::alloc::{Allocator, Global, Layout, handle_alloc_error};

fn main() {
    let layout = Layout::new::<i32>();
    
    // Attempt to allocate memory for an i32 using the Global allocator
    match Global.allocate(layout) {
        Ok(ptr) => {
            // Success: Deallocate the memory to avoid leaks and pass Miri checks
            unsafe {
                Global.deallocate(ptr.cast(), layout);
            }
        }
        Err(_) => {
            // Failure: Call the error handler only if allocation actually fails
            handle_alloc_error(layout);
        }
    }
}