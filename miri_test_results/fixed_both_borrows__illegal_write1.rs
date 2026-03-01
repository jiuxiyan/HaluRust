fn main() {
    let mut target = Box::new(42u32); 
    let xref = &mut *target; // Create a mutable reference
    {
        let x: *mut u32 = xref as *mut u32; // Derive a raw pointer from a mutable source
        unsafe { *x = 42 }; // Sound, because 'x' is derived from a mutable borrow
    }
    let _x = *xref;
}