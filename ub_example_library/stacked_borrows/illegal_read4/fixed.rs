fn main() {
    let mut x = 2;
    let xref1 = &mut x;
    let xraw = xref1 as *mut _;
    
    // Safety: xraw is derived from a valid mutable reference to x.
    let xref2 = unsafe { &mut *xraw };
    
    // Use the derived reference first. 
    // In the Stacked Borrows model, this is valid as xref2 is at the top of the stack.
    let _val_from_ref = *xref2;
    
    // Now use the raw pointer. This is allowed, but it invalidates xref2 
    // because accessing a parent pointer (xraw) pops the child borrow (xref2) 
    // from the borrow stack.
    let _val_from_raw = unsafe { *xraw };
}