#![allow(dead_code)]

// We use packed structs to get around alignment restrictions
#[repr(C, packed)]
struct Data {
    pad: u8,
    ptr: &'static i32,
}

// But we need to guarantee some alignment
struct Wrapper {
    align: u64,
    data: Data,
}

static G: i32 = 0;

fn main() {
    let mut w = Wrapper { align: 0, data: Data { pad: 0, ptr: &G } };

    // To fix the Undefined Behavior, we must:
    // 1. Use addr_of! to get the address of the 'ptr' field. This correctly
    //    calculates the offset (1 byte) and avoids creating an intermediate
    //    unaligned reference, which is UB.
    let d_ptr = std::ptr::addr_of!(w.data.ptr);

    unsafe {
        // 2. Use read_unaligned to safely load the pointer from the packed struct.
        //    This handles the fact that 'ptr' is not aligned to its natural boundary.
        let x: &'static i32 = std::ptr::read_unaligned(d_ptr);
        
        // 3. Now 'x' is a valid, correctly aligned reference to G.
        let _val = *x;
    }
}