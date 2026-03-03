use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, AtomicU32, Ordering};
use std::thread;

fn main() {
    // Use AtomicU32 instead of static mut to prevent data races
    static V: AtomicU32 = AtomicU32::new(0);
    
    let a = Arc::new(AtomicUsize::default());
    let b = a.clone();
    
    let handle = thread::spawn(move || {
        V.store(1, Ordering::Relaxed);
        // Release ordering ensures V.store is visible to anyone who acquires this store
        b.store(1, Ordering::Release);
    });

    // Instead of sleep, wait for the signal with Acquire ordering to establish happens-before
    while a.load(Ordering::Acquire) != 1 {
        std::hint::spin_loop();
    }

    // Now it is safe to read from and write to V
    assert_eq!(V.load(Ordering::Relaxed), 1);
    V.store(2, Ordering::Relaxed);
    
    handle.join().unwrap();
}