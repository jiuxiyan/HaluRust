use std::cell::RefCell;
use std::panic;

pub struct NoisyDrop {}

impl Drop for NoisyDrop {
    fn drop(&mut self) {
        panic!("ow");
    }
}

thread_local! {
    // Wrap in RefCell and Option to allow manual extraction and dropping before thread exit
    pub static NOISY: RefCell<Option<NoisyDrop>> = RefCell::new(Some(NoisyDrop {}));
}

fn main() {
    // Access the thread-local to ensure it is initialized
    NOISY.with(|_| ());

    // Manually trigger the drop inside a catch_unwind block.
    // This prevents the panic from occurring during the automatic TLS teardown phase,
    // which would otherwise cause the runtime to abort the process.
    let _ = NOISY.with(|slot| {
        // Extract the value from the RefCell first to avoid capturing a &RefCell
        // inside the catch_unwind closure, which would violate UnwindSafe.
        let val = slot.borrow_mut().take();

        // Move the extracted value into the catch_unwind closure.
        // Option<NoisyDrop> is UnwindSafe, so the closure becomes UnwindSafe.
        panic::catch_unwind(move || {
            // Taking the value out of the Option and letting it drop here
            drop(val);
        })
    });
}