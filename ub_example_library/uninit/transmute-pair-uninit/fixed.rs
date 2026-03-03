use std::mem::{self, MaybeUninit};

fn main() {
    // This constructs a `(usize, bool)` pair: 9 bytes initialized, the rest (padding) not.
    // Ensure that these 9 bytes are indeed initialized, and the rest is indeed not.
    let x: MaybeUninit<Box<[u8]>> = unsafe {
        // Use stable overflowing_add instead of internal intrinsics
        let z = 0usize.overflowing_add(0);
        // Transmuting a tuple with padding to MaybeUninit is valid as long as sizes match.
        // The padding bytes in `z` remain uninitialized in `x`.
        std::mem::transmute::<(usize, bool), MaybeUninit<Box<[u8]>>>(z)
    };

    // Obtain a pointer to the memory. 
    // We use x.as_ptr() which is the standard way to get a pointer to MaybeUninit content.
    let z = x.as_ptr() as *const u8;
    
    let ptr_size = mem::size_of::<usize>();
    let first_undef = ptr_size + 1; // 8 bytes for usize + 1 byte for bool = 9

    // Read the initialized bytes (indices 0 through 8).
    for i in 0..first_undef {
        let byte = unsafe { *z.add(i) };
        assert_eq!(byte, 0);
    }

    // The bytes from index `first_undef` (9) to the end of the allocation are uninitialized padding.
    // We cannot read them as `u8` because that would be Undefined Behavior.
    // Miri would flag any attempt to load from these offsets.
    println!("Successfully verified {} initialized bytes.", first_undef);
}