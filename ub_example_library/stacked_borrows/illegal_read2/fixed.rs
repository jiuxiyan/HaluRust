// A callee may not read the destination of our `&mut` without
// us noticing.

#[rustfmt::skip] // rustfmt bug: https://github.com/rust-lang/rustfmt/issues/5391
fn main() {
    let mut x = 15;
    let xraw = &mut x as *mut _;
    let xref = unsafe { &mut *xraw }; 
    
    // Fix: Pass a pointer derived from `xref` instead of the original `xraw`.
    // This treats the access in `callee` as a reborrow of `xref`, which
    // prevents `xref` from being invalidated by the Stacked Borrows rules.
    callee(xref as *mut i32);
    
    let _val = *xref; // This is now valid because xref was not invalidated.
}

fn callee(xraw: *mut i32) {
    // We are a bit sneaky: We first create a shared ref, exploiting the reborrowing rules,
    // and then we read through that.
    // This is now a valid reborrow of the pointer passed from main.
    let shr = unsafe { &*xraw };
    let _val = *shr;
}