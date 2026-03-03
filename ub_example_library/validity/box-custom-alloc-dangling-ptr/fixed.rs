#![feature(allocator_api)]
use std::alloc::{Allocator, Layout, AllocError};
use std::ptr::NonNull;

#[allow(unused)]
struct MyAlloc(usize, usize); // make sure `Box<T, MyAlloc>` is an `Aggregate`

unsafe impl Allocator for MyAlloc {
    fn allocate(&self, layout: Layout) -> Result<NonNull<[u8]>, AllocError> {
        // Handle ZSTs: std::alloc::alloc is UB for size 0
        if layout.size() == 0 {
            let raw_ptr = layout.align() as *mut u8;
            let slice_ptr = std::ptr::slice_from_raw_parts_mut(raw_ptr, 0);
            return Ok(unsafe { NonNull::new_unchecked(slice_ptr) });
        }

        let raw_ptr = unsafe { std::alloc::alloc(layout) };
        if raw_ptr.is_null() {
            return Err(AllocError);
        }
        let slice_ptr = std::ptr::slice_from_raw_parts_mut(raw_ptr, layout.size());
        Ok(unsafe { NonNull::new_unchecked(slice_ptr) })
    }

    unsafe fn deallocate(&self, ptr: NonNull<u8>, layout: Layout) {
        // Handle ZSTs: std::alloc::dealloc is UB for size 0
        if layout.size() == 0 {
            return;
        }
        
        unsafe {
            // Fix typo: deallocate -> dealloc
            std::alloc::dealloc(ptr.as_ptr(), layout);
        }
    }
}

fn main() {
    let alloc = MyAlloc(0, 0);
    let layout = Layout::new::<i32>();
    
    // 1. Allocate valid memory using the custom allocator
    let ptr = match alloc.allocate(layout) {
        Ok(p) => p.cast::<i32>(),
        Err(_) => return,
    };
    
    // 2. Initialize the memory (Box expects initialized content for non-MaybeUninit types)
    unsafe {
        ptr.as_ptr().write(42);
    }

    // 3. Construct the Box using the official API instead of transmute.
    // This ensures the Box invariant (valid pointer with provenance) is satisfied.
    let _b: Box<i32, MyAlloc> = unsafe {
        Box::from_raw_in(ptr.as_ptr(), alloc)
    };
    
    // _b will now safely deallocate via MyAlloc when it goes out of scope.
}