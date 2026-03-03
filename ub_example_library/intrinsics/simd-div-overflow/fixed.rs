#![feature(core_intrinsics, repr_simd)]

use std::intrinsics::simd::{simd_div, simd_eq, simd_and, simd_select};

#[repr(simd)]
#[allow(non_camel_case_types)]
#[derive(Copy, Clone)]
struct i32x2([i32; 2]);

#[repr(simd)]
#[allow(non_camel_case_types)]
#[derive(Copy, Clone)]
struct m32x2([i32; 2]);

fn main() {
    unsafe {
        let x = i32x2([1, i32::MIN]);
        let y = i32x2([1, -1]);

        // Detect potential overflow: (dividend == i32::MIN) AND (divisor == -1)
        let is_min = i32x2([i32::MIN, i32::MIN]);
        let is_neg_one = i32x2([-1, -1]);
        
        let mask_min: m32x2 = simd_eq(x, is_min);
        let mask_neg_one: m32x2 = simd_eq(y, is_neg_one);
        let overflow_mask: m32x2 = simd_and(mask_min, mask_neg_one);

        // Sanitize divisor: replace -1 with 1 where overflow would occur to avoid UB
        let safe_y = simd_select(overflow_mask, i32x2([1, 1]), y);

        // Perform division safely
        let result = simd_div(x, safe_y);

        // Restore the result for overflow lanes (i32::MIN / -1 is defined as i32::MIN in wrapping math)
        let _final_result: i32x2 = simd_select(overflow_mask, is_min, result);
    }
}