#![allow(internal_features)]
#![feature(core_intrinsics, custom_mir)]

use std::intrinsics::mir::*;
use std::num::NonZero;
use std::ptr;

fn f(c: u32) {
    println!("{c}");
}

// Call that function in a way that respects the `NonZero<u32>` invariant.
#[custom_mir(dialect = "runtime", phase = "optimized")]
fn call(f: fn(NonZero<u32>)) {
    mir! {
        let _res: ();
        {
            // Fix: Use a non-zero value to satisfy the NonZero<u32> invariant.
            let c = 1u32;
            let tmp = ptr::addr_of!(c);
            let ptr = tmp as *const NonZero<u32>;
            // The call site now receives a valid `NonZero<u32>`.
            Call(_res = f(*ptr), ReturnTo(retblock), UnwindContinue())
        }
        retblock = {
            Return()
        }
    }
}

fn main() {
    // Transmuting function pointers is generally risky, but here we ensure 
    // the argument passed (NonZero<u32>) is bit-compatible with the target (u32).
    let f_ptr: fn(NonZero<u32>) = unsafe { std::mem::transmute(f as fn(u32)) };
    call(f_ptr);
}