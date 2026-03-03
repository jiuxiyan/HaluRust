// A case that is not covered by `mixed_size_read_write`.

use std::sync::atomic::*;
use std::thread;

fn main() {
    let data = AtomicI32::new(0);

    thread::scope(|s| {
        s.spawn(|| {
            // Use a safe atomic load instead of a raw pointer read to avoid data races.
            let _val = data.load(Ordering::Relaxed);
            
            // Instead of casting to AtomicI8 (which is UB due to mixed-size atomic access),
            // use fetch_update to atomically modify only the relevant bits of the i32.
            let _ = data.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |old| {
                // Simulate a compare_exchange on the first byte (lowest 8 bits).
                let first_byte = (old & 0xFF) as i8;
                if first_byte == 0 {
                    // If the byte is 0, replace it with 1.
                    Some((old & !0xFF) | 1)
                } else {
                    // Otherwise, the "comparison" failed.
                    None
                }
            });
            
            thread::yield_now();
        });
        s.spawn(|| {
            let _val = data.load(Ordering::Relaxed);
        });
    });
}