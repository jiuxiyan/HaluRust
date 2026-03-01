use std::mem;
use std::ptr;

// We have three fields to avoid the ScalarPair optimization.
#[allow(unused)]
enum E {
    None,
    Some(&'static (), &'static (), usize),
}

fn main() {
    unsafe {
        let mut p: mem::MaybeUninit<E> = mem::MaybeUninit::zeroed();
        
        // FIX: Instead of transmuting the tuple to E (which creates a value where 
        // non-discriminant bytes are considered padding), we write the raw 
        // bit pattern of the tuple directly into the buffer. 
        // This ensures that all bytes are marked as "initialized" in the 
        // abstract machine, preventing the subsequent read from being UB.
        let p_raw = p.as_mut_ptr() as *mut (usize, usize, usize);
        ptr::write_unaligned(p_raw, (0usize, 0usize, 0usize));

        // This is a `None`, so everything but the discriminant is padding 
        // from the perspective of the type E, but the underlying memory 
        // remains initialized because we performed a raw write of a tuple.
        assert!(matches!(*p.as_ptr(), E::None));

        // Turns out the discriminant is (currently) stored
        // in the 1st pointer, so the second half is padding.
        let c = &p as *const _ as *const u8;
        let padding_offset = mem::size_of::<&'static ()>();
        
        // Read a byte. This is now safe because the memory was initialized 
        // as part of the raw tuple write.
        let _val = *c.add(padding_offset);
    }
}