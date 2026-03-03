fn main() {
    // Ensure the local variable has a size of at least 1 byte
    let x_val: i8 = 0;
    let x = &x_val as *const i8;
    
    // This is now safe because x points to an allocation of 1 byte
    let _val = unsafe { *x };
}