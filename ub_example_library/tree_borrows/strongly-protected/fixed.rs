fn inner(x: &mut i32, f: fn(*mut i32)) {
    // `f` may mutate, but it may not deallocate!
    // `f` takes a raw pointer so that the only protector
    // is that on `x`
    f(x)
}

fn main() {
    // We use a standard Box instead of leaking it. 
    // This allows Rust to manage the memory safely.
    let mut val = Box::new(0);
    
    // We pass a mutable reference to `inner`. 
    // The memory will be deallocated automatically when `val` goes out of scope,
    // which happens after `inner` has finished executing, respecting the protector on `x`.
    inner(&mut val, |raw| {
        // The callback can safely mutate the value via the raw pointer.
        // However, it must not attempt to deallocate the memory (e.g., via Box::from_raw).
        unsafe {
            *raw = 42;
        }
    });
}