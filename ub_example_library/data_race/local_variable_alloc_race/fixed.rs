#![feature(core_intrinsics)]
#![feature(custom_mir)]

use std::intrinsics::mir::*;
use std::sync::atomic::Ordering::*;
use std::sync::atomic::*;
use std::thread::JoinHandle;

static P: AtomicPtr<u8> = AtomicPtr::new(core::ptr::null_mut());

fn spawn_thread() -> JoinHandle<()> {
    std::thread::spawn(|| {
        // Use Acquire to synchronize with the Release store in the main thread.
        while P.load(Acquire).is_null() {
            std::hint::spin_loop();
        }
        unsafe {
            // Initialize `*P`.
            let ptr = P.load(Acquire);
            *ptr = 127;
        }
    })
}

fn finish(t: JoinHandle<()>, val_ptr: *mut u8) {
    // Use Release to ensure the StorageLive(val) event happens-before the pointer is visible.
    P.store(val_ptr, Release);

    // Wait for the thread to be done.
    t.join().unwrap();

    // Read initialized value.
    assert_eq!(unsafe { *val_ptr }, 127);
}

#[custom_mir(dialect = "runtime", phase = "optimized")]
fn main() {
    mir! {
        let t;
        let val;
        let val_ptr;
        let _ret;
        {
            Call(t = spawn_thread(), ReturnTo(after_spawn), UnwindContinue())
        }
        after_spawn = {
            // This allocation event must be synchronized with the access in the other thread.
            StorageLive(val);

            val_ptr = &raw mut val;
            Call(_ret = finish(t, val_ptr), ReturnTo(done), UnwindContinue())
        }
        done = {
            Return()
        }
    }
}