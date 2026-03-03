use std::thread;

fn main() {
    race(0);
}

// Using an argument for the ptr to point to, since those do not get StorageDead.
fn race(local: i32) {
    // thread::scope ensures all threads spawned within are joined 
    // before the function returns, preventing the Use-After-Free.
    thread::scope(|s| {
        s.spawn(|| {
            // We can now safely reference `local` from the parent stack.
            // Scoped threads allow borrowing from the local stack frame.
            let _val = local;
        });
        // Make the other thread go first. 
        // Because of the scope, the main thread will wait for the spawned 
        // thread to finish before `race` returns and `local` is dropped.
        thread::yield_now();
    });
}