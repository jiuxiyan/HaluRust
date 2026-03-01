fn main() {
    // Change f to accept a raw pointer to handle nullability safely.
    // In Rust, references (&T) must never be null. Raw pointers (*const T) can be.
    fn f(x: *const i32) {
        // Safely convert the raw pointer to an Option<&i32>.
        // x.as_ref() returns None if the pointer is null.
        // It is unsafe because if the pointer is not null, it must be valid and aligned.
        let x_ref = unsafe { x.as_ref() };
        
        match x_ref {
            Some(val) => println!("Value: {}", val),
            None => println!("Received a null pointer"),
        }
    }

    // No transmute needed; use the function with its actual signature.
    let g: fn(*const i32) = f;

    // Call with a null pointer. This is now safe and well-defined.
    g(std::ptr::null())
}