/// Case 3: Reading uninitialized memory via MaybeUninit misuse

use std::mem::MaybeUninit;

pub fn create_array() -> [i32; 5] {
    let mut arr: [MaybeUninit<i32>; 5] = unsafe { MaybeUninit::uninit().assume_init() };

    // Only initialize 3 out of 5 elements
    for i in 0..3 {
        arr[i] = MaybeUninit::new(i as i32 * 10);
    }

    // UB: transmuting partially-initialized array
    unsafe { std::mem::transmute(arr) }
}
