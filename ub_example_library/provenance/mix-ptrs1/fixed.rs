use std::{mem, ptr};

const PTR_SIZE: usize = mem::size_of::<&i32>();

fn main() {
    unsafe {
        let ptr = &0 as *const i32;
        let arr = [ptr; 2];
        // We want to do a scalar read of a pointer at offset PTR_SIZE/2 into this array. But we
        // cannot use a packed struct or `read_unaligned`, as those use the memcpy code path in
        // Miri. So instead we shift the entire array by a bit and then the actual read we want to
        // do is perfectly aligned.
        let mut target_arr = [ptr::null::<i32>(); 3];
        let target = target_arr.as_mut_ptr().cast::<u8>();
        target.add(PTR_SIZE / 2).cast::<[*const i32; 2]>().write_unaligned(arr);
        // Now target_arr[1] is a mix of the two `ptr` we had stored in `arr`.
        // They all have the same provenance, but not in the right order, so we reject this.
        let _strange_ptr = target_arr[1];
        
        // To fix the UB, we must use a pointer that has valid provenance and a valid address.
        // `_strange_ptr` lost its provenance because it was constructed from pieces of 
        // different pointer writes, and its address was corrupted by the byte-shifting.
        // We use `ptr.with_addr(...)` to combine the valid provenance of `ptr` with 
        // the correct address from `ptr.addr()`.
        assert_eq!(*ptr.with_addr(ptr.addr()), 0);
    }
}