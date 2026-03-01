fn inner(x: &mut i32, f: fn(&mut i32)) {
    // `f` may mutate, but it may not deallocate!
    f(x)
}

fn main() {
    // Keep ownership of the Box in main instead of leaking it.
    let mut b = Box::new(0);
    
    // Pass a mutable reference to inner.
    inner(&mut b, |x| {
        // Mutate the value safely without attempting to deallocate the underlying memory.
        *x += 1;
    });
    
    // The Box is safely dropped here at the end of main's scope.
}