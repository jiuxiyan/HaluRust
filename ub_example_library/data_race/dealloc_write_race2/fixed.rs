use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread::spawn;

fn main() {
    // Use Arc for shared ownership and AtomicUsize for thread-safe mutation.
    // This replaces manual memory management and raw pointers, which were causing
    // Use-After-Free and Data Race Undefined Behavior.
    let pointer = Arc::new(AtomicUsize::new(0));

    // Clone the Arc for the first thread.
    let ptr1 = Arc::clone(&pointer);
    let j1 = spawn(move || {
        // In the original code, this thread manually deallocated the memory.
        // With Arc, the memory is safely reclaimed only when the last reference is dropped.
        drop(ptr1);
    });

    // Clone the Arc for the second thread.
    let ptr2 = Arc::clone(&pointer);
    let j2 = spawn(move || {
        // Use an atomic store to update the value. This prevents the data race
        // detected by Miri and ensures the operation is thread-safe.
        ptr2.store(2, Ordering::SeqCst);
    });

    // Wait for both threads to complete.
    j1.join().unwrap();
    j2.join().unwrap();

    // The memory is automatically and safely deallocated here when the last Arc ('pointer') 
    // goes out of scope.
}