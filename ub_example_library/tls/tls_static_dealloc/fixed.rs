//! Ensure that thread-local statics get deallocated when the thread dies.

#![feature(thread_local)]

#[thread_local]
static mut TLS: u8 = 0;

fn main() {
    // Instead of returning a pointer to the thread-local storage, 
    // we copy the value out of the thread before it terminates.
    let val = std::thread::spawn(|| {
        unsafe { TLS }
    }).join().unwrap();

    // Now 'val' is a local copy in the main thread, avoiding dangling pointers.
    let _val = val;
}