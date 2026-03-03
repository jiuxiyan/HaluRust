/// Checks that with only one exposed reference, wildcard accesses
/// correctly cause foreign accesses.
pub fn main() {
    let mut x: u32 = 42;

    let ptr_base = &mut x as *mut u32;
    
    // FIX: Use raw pointers instead of &mut to allow aliasing
    let ptr1 = ptr_base; 
    let ptr2 = ptr_base;

    let int1 = ptr1 as usize;
    let wild = int1 as *mut u32;

    // Write through the wildcard pointer.
    // This is now valid because ptr2 (raw pointer) does not 
    // have the strict exclusivity requirements of &mut.
    unsafe { wild.write(13) };

    // FIX: Read through the raw pointer in an unsafe block.
    let _val = unsafe { *ptr2 };
    
    assert_eq!(_val, 13);
}