fn main() {
    let mut data: i32 = 0;
    let ptr: *mut i32 = &mut data;
    unsafe {
        // This is now safe because ptr points to a valid stack allocation
        *ptr = 0i32;
    }
}