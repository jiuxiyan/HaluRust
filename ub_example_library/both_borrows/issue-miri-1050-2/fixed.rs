use std::ptr::NonNull;

fn main() {
    unsafe {
        // Create a valid allocation on the heap
        let original_box = Box::new(42);
        
        // Convert the Box into a raw pointer, transferring ownership
        let raw_ptr: *mut i32 = Box::into_raw(original_box);
        
        // Wrap the raw pointer in NonNull
        let ptr = NonNull::new_unchecked(raw_ptr);
        
        // Reconstruct the Box from the valid raw pointer to safely deallocate it
        drop(Box::from_raw(ptr.as_ptr()));
    }
}