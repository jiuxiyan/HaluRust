// We want to control preemption here. Stacked borrows interferes by having its own accesses.

use std::mem::MaybeUninit;
use std::ptr::null_mut;
use std::sync::atomic::{AtomicPtr, Ordering};
use std::thread::spawn;

#[derive(Copy, Clone)]
struct EvilSend<T>(pub T);

unsafe impl<T> Send for EvilSend<T> {}
unsafe impl<T> Sync for EvilSend<T> {}

fn main() {
    // Shared atomic pointer
    let pointer = AtomicPtr::new(null_mut::<MaybeUninit<usize>>());
    let ptr = EvilSend(&pointer as *const AtomicPtr<MaybeUninit<usize>>);

    // Note: this is scheduler-dependent
    // the operations need to occur in
    // order, otherwise the allocation is
    // not visible to the other-thread to
    // detect the race:
    //  1. alloc
    //  2. write
    unsafe {
        let j1 = spawn(move || {
            let ptr = ptr; // avoid field capturing
            // Concurrent allocate the memory.
            // Use Release ordering to synchronize the allocation with the Acquire load.
            let pointer = &*ptr.0;
            pointer.store(Box::into_raw(Box::new_uninit()), Ordering::Release);
        });

        let j2 = spawn(move || {
            let ptr = ptr; // avoid field capturing
            let pointer = &*ptr.0;

            // Use Acquire ordering to establish a happens-before relationship with the Release store.
            let raw_ptr = pointer.load(Ordering::Acquire);
            if !raw_ptr.is_null() {
                // Safety: Acquire ordering ensures the allocation is visible.
                let _ = *raw_ptr;
            }
        });

        j1.join().unwrap();
        j2.join().unwrap();

        // Clean up memory
        let final_ptr = pointer.load(Ordering::Acquire);
        if !final_ptr.is_null() {
            drop(Box::from_raw(final_ptr));
        }
    }
}