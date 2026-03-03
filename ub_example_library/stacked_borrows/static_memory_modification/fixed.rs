use std::sync::atomic::{AtomicUsize, Ordering};

// Use AtomicUsize for safe, shared global mutability
static X: AtomicUsize = AtomicUsize::new(5);

fn main() {
    // Modifying the value safely using atomic methods
    X.store(10, Ordering::SeqCst);
    
    // Reading the value safely
    let _x = X.load(Ordering::SeqCst);
}