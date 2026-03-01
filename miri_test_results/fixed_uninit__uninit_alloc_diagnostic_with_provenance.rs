#![allow(dropping_copy_types)]

// Test printing allocations that contain single-byte provenance.

use std::alloc::{Layout, alloc, dealloc};
use std::mem::{self, MaybeUninit};
use std::slice::from_raw_parts;
use std::ptr;

fn byte_with_provenance<T>(val: u8, prov: *const T, frag_idx: usize) -> MaybeUninit<u8> {
    // Use the correct size for the array literal to create a usize address
    let ptr = prov.with_addr(usize::from_ne_bytes([val; mem::size_of::<usize>()]));
    // Transmute the pointer into its constituent bytes (as MaybeUninit to preserve provenance)
    let bytes: [MaybeUninit<u8>; mem::size_of::<*const ()>()] = unsafe { mem::transmute(ptr) };
    bytes[frag_idx]
}

fn main() {
    let layout = Layout::from_size_align(16, 8).unwrap();
    unsafe {
        let ptr = alloc(layout);
        // Check for allocation failure
        if ptr.is_null() {
            std::alloc::handle_alloc_error(layout);
        }

        // Fix: Initialize the entire allocation to zero to avoid reading uninitialized memory.
        // Reading uninitialized memory is UB, even for u8 comparison.
        ptr::write_bytes(ptr, 0, layout.size());

        let ptr_raw = ptr.cast::<MaybeUninit<u8>>();
        
        // Overwrite specific bytes with provenance fragments or literal values
        *ptr_raw.add(0) = byte_with_provenance(0x42, &42u8, 0);
        *ptr.add(1) = 0x12;
        *ptr.add(2) = 0x13;
        *ptr_raw.add(3) = byte_with_provenance(0x43, &0u8, 1);

        // Now both slices point to fully initialized memory (some bytes carry provenance)
        let slice1 = from_raw_parts(ptr, 8);
        let slice2 = from_raw_parts(ptr.add(8), 8);
        
        // This comparison is now safe because all bytes in the 16-byte block are initialized
        drop(slice1.cmp(slice2));
        
        dealloc(ptr, layout);
    }
}