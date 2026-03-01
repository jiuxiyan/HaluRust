use std::alloc::{Layout, alloc, dealloc, realloc};

fn main() {
    unsafe {
        let layout = Layout::from_size_align_unchecked(1, 1);
        
        // 1. Initial allocation
        let x = alloc(layout);
        if x.is_null() {
            return;
        }

        // 2. Resize the allocation
        // The premature dealloc(x, layout) is removed because realloc 
        // requires a valid, currently allocated pointer.
        let new_size = 1;
        let z = realloc(x, layout, new_size);
        
        if z.is_null() {
            // If realloc fails, the original pointer x remains valid and must be freed.
            dealloc(x, layout);
        } else {
            // 3. Clean up the final allocation
            // The layout used for dealloc must match the size and alignment of the actual allocation.
            let final_layout = Layout::from_size_align_unchecked(new_size, 1);
            dealloc(z, final_layout);
        }
    }
}