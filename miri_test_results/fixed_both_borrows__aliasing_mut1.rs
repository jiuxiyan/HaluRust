fn safe(x: *mut i32, y: *mut i32) {
    // Safety: The caller must ensure these pointers are valid for writes.
    // Raw pointers do not have the same exclusivity requirements as &mut references.
    unsafe {
        *x = 1;
        *y = 2;
    }
}

fn main() {
    let mut x = 0;
    // Obtain a raw pointer to the data. 
    // We use 'as' cast instead of transmute for clarity and safety.
    let xraw: *mut i32 = &mut x as *mut i32;
    
    // Call the function directly with aliasing raw pointers.
    // This is sound because raw pointers are allowed to alias.
    safe(xraw, xraw);
}