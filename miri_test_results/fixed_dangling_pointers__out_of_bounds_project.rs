use std::ptr::addr_of;

fn main() {
    // Increase the size of the allocation to match the target type
    let v = (0u32, 0u32, 0u32);
    let ptr = addr_of!(v);
    unsafe {
        // These are now within the bounds of the 12-byte allocation
        let _field = addr_of!((*ptr).1); 
        let _field = addr_of!((*ptr).2);
    }
}