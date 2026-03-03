#![feature(core_intrinsics, repr_simd)]

use std::intrinsics::simd::{simd_shr, simd_and};

#[repr(simd)]
#[allow(non_camel_case_types)]
struct i32x2([i32; 2]);

fn main() {
    unsafe {
        let x = i32x2([1, 1]);
        let y = i32x2([20, 40]);
        
        // Mask the shift amount to be within 0..31
        // This prevents UB by ensuring the shift count is always valid.
        let mask = i32x2([31, 31]);
        
        // Use simd_and to perform bitwise AND on the vectors.
        // This avoids projecting into the SIMD type (e.g., y.0[0]), 
        // which is prohibited by modern Rust SIMD constraints (MCP#838).
        let sanitized_y = simd_and(y, mask);
        
        simd_shr(x, sanitized_y);
    }
}