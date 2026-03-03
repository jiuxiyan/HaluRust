use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;
use std::time::Duration;

fn main() {
    // Shared atomic variable to prevent data races.
    // It is declared here to ensure it outlives the threads that use it.
    let stack_var = AtomicUsize::new(0);

    // Use thread::scope to safely share references to stack variables.
    // This ensures that all spawned threads are joined before the scope ends,
    // preventing the use-after-free (deallocation race) detected by Miri.
    thread::scope(|s| {
        s.spawn(|| {
            // Thread 1: Simulate the timing of the original code.
            // In the original, this thread owned the stack variable.
            // Now, it simply waits while the variable is safely managed by the scope.
            thread::sleep(Duration::from_millis(200));
        });

        s.spawn(|| {
            // Thread 2: Perform an atomic write to the shared variable.
            // This replaces the unsafe raw pointer dereference and prevents data races.
            stack_var.store(3, Ordering::Release);
        });
    });

    // After the scope ends, both threads are guaranteed to have finished.
    // We can safely access the final value.
    let final_value = stack_var.load(Ordering::Acquire);
    assert_eq!(final_value, 3);
}