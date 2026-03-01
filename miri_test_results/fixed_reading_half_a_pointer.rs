#![allow(dead_code)]

// Use raw pointers in packed structs to avoid alignment invariant issues with references.
// References must always be aligned, but fields in a packed struct might not be.
#[repr(C, packed)]
struct Data {
    pad: u8,
    ptr: *const i32,
}

// But we need to guarantee some alignment
struct Wrapper {
    align: u64,
    data: Data,
}

static G: i32 = 0;

fn main() {
    // Initialize with a raw pointer cast to avoid reference alignment issues.
    let w = Wrapper { 
        align: 0, 
        data: Data { 
            pad: 0, 
            ptr: &G as *const i32 
        } 
    };

    // Use addr_of! to get the address of the field 'ptr' within the packed struct.
    // This correctly handles the 1-byte offset without creating an unaligned reference.
    // The type of ptr_field_addr is *const *const i32.
    let ptr_field_addr = std::ptr::addr_of!(w.data.ptr);

    unsafe {
        // Since the field is in a packed struct at offset 1, it is unaligned.
        // We must use read_unaligned to safely load the pointer value.
        // read_unaligned<*const i32>(src: *const *const i32) -> *const i32
        let x: *const i32 = std::ptr::read_unaligned(ptr_field_addr);

        // Now x contains the correct address of G, and can be safely dereferenced.
        // G is a static i32, so it is guaranteed to be aligned and valid.
        let _val = *x;
    }
}