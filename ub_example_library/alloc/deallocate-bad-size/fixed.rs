use std::alloc::{alloc, dealloc, Layout};

fn main() {
    unsafe {
        // 1. Define the layout once
        let layout = Layout::from_size_align(1, 1).unwrap();
        
        // 2. Perform the allocation
        let x = alloc(layout);
        
        // 3. Check for null pointer (allocation failure)
        if x.is_null() {
            std::alloc::handle_alloc_error(layout);
        }
        
        // 4. Deallocate using the exact same layout
        dealloc(x, layout);
    }
}