// Make sure that we cannot pass by argument a `&` that got already invalidated.
fn foo(_: Option<&i32>) {}

fn main() {
    let mut val = 42;
    let xraw = &mut val as *mut i32;
    
    // Perform the write access first to avoid invalidating an existing shared reference.
    unsafe { *xraw = 42 }; 
    
    // Create the shared reference AFTER the write is complete.
    let some_xref = unsafe { Some(&*xraw) };
    
    // Now the reference is valid to pass to the function.
    foo(some_xref);
}