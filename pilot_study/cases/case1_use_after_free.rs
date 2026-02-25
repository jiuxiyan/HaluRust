/// Case 1: Use-after-free via raw pointer
/// A classic UB where a raw pointer outlives the data it points to.

pub fn get_value() -> i32 {
    let ptr: *const i32;
    {
        let val = Box::new(42);
        ptr = &*val as *const i32;
        // val is dropped here
    }
    unsafe { *ptr }
}
