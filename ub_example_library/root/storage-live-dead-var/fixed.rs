#![feature(core_intrinsics, custom_mir)]
use std::intrinsics::mir::*;

#[custom_mir(dialect = "runtime")]
fn main() {
    mir! {
        let val: i32;
        {
            StorageLive(val); // Mark storage as live BEFORE access
            val = 42;         // Now this access is valid
            StorageDead(val); // Mark storage as dead before returning
            Return()
        }
    }
}