#![feature(core_intrinsics, portable_simd)]

use std::intrinsics::simd::*;
use std::simd::*;

fn main() {
    unsafe {
        let buf = Simd::<i32, 8>::splat(0);
        // Change SimdAlign::Vector to SimdAlign::Element to match the actual pointer alignment.
        // The pointer is aligned to i32 (4 bytes), but not to i32x4 (16 bytes).
        simd_masked_load::<_, _, _, { SimdAlign::Element }>(
            i32x4::splat(-1),
            buf.as_array()[1..].as_ptr(),
            i32x4::splat(0),
        );
    }
}