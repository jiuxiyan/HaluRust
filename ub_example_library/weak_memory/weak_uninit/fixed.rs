// Tests showing weak memory behaviours are exhibited. All tests
// return true when the desired behaviour is seen.
// This is scheduler and pseudo-RNG dependent, so each test is
// run multiple times until one try returns true.
// Spurious failure is possible, if you are really unlucky with
// the RNG and always read the latest value from the store buffer.

use std::sync::atomic::*;
use std::thread::spawn;

#[allow(dead_code)]
#[derive(Copy, Clone)]
struct EvilSend<T>(pub T);

unsafe impl<T> Send for EvilSend<T> {}
unsafe impl<T> Sync for EvilSend<T> {}

// We can't create static items because we need to run each test multiple times.
fn static_uninit_atomic() -> &'static AtomicUsize {
    // Properly initialize the atomic to 0 before leaking it to avoid UB
    Box::leak(Box::new(AtomicUsize::new(0)))
}

fn relaxed() {
    let x = static_uninit_atomic();
    let j1 = spawn(move || {
        x.store(1, Ordering::Relaxed);
    });

    let j2 = spawn(move || x.load(Ordering::Relaxed));

    j1.join().unwrap();
    j2.join().unwrap();
}

fn main() {
    // If we try often enough, we should hit UB.
    for _ in 0..100 {
        relaxed();
    }
}