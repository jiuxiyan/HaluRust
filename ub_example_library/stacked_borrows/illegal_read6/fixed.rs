fn main() {
    unsafe {
        let mut val = 0;
        let x = &mut val;
        // We create the raw pointer from the current valid mutable reference.
        // We avoid the redundant re-borrow `let x = &mut *x;` which would 
        // invalidate any raw pointers previously derived from `x`.
        let raw = x as *mut _;
        let _y = &*x; 
        let _val = *raw;
    }
}