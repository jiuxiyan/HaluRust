fn main() {
    unsafe {
        // Allocate as u16
        let ptr = Box::into_raw(Box::new(0u16));
        
        // Reconstruct as u16 to ensure layout matches for deallocation.
        // Reinterpreting a 2-byte allocation as a 4-byte u32 is Undefined Behavior.
        drop(Box::from_raw(ptr));
    }
}