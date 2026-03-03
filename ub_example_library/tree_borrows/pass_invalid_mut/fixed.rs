fn foo(nope: &mut i32) {
    *nope = 31;
}

fn main() {
    let x = &mut 42;
    let xraw = x as *mut _;
    let xref = unsafe { &mut *xraw };
    *xref = 18; // activate xref
    // FIX: Read from the reference 'xref' instead of the raw pointer 'xraw'.
    // Reading from a parent pointer (xraw) would invalidate the child mutable reference (xref) for writing.
    let _val = *xref; 
    foo(xref);
}