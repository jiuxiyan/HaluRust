use std::sync::atomic::{AtomicI32, Ordering};

fn main() {
    // Declare the static as an AtomicI32 to ensure it's placed in 
    // memory that supports atomic operations and interior mutability.
    static X: AtomicI32 = AtomicI32::new(0);
    
    // Use the atomic directly. AtomicI32 provides interior mutability,
    // so we can call compare_exchange on a shared reference.
    X.compare_exchange(1, 2, Ordering::Relaxed, Ordering::Relaxed).unwrap_err();
}