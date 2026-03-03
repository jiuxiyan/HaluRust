fn main() {
    // 1. Create a valid allocation on the stack
    let val: i32 = 44;
    
    // 2. Derive a pointer from the valid allocation (preserves provenance)
    let p = &val as *const i32;
    
    // 3. Dereferencing is now sound because p points to a valid i32
    let x = unsafe { *p };
    
    println!("Value accessed via pointer: {}", x);
}