/// Checks with multiple exposed nodes, that if they are all disabled
/// then no wildcard accesses are possible.
pub fn main() {
    let mut x: u32 = 42;

    let ptr_base = &mut x as *mut u32;
    
    // Use raw pointers instead of &mut to allow aliasing without invalidation.
    let ref1 = ptr_base;
    let ref2 = ptr_base;
    let ref3 = ptr_base;

    // Both pointers get exposed via integer cast.
    let int1 = ref1 as usize;
    let _int2 = ref2 as usize;

    let wild = int1 as *mut u32;

    // This write is valid because ref3 is a raw pointer and 
    // does not invalidate its siblings (ref1, ref2) in the same way &mut would.
    unsafe { *ref3 = 13 };

    // This access is now valid because the provenance of ref1 (and thus wild)
    // was not invalidated by the write through ref3.
    let _val = unsafe { *wild };
}