//! Make sure we detect erroneous constants post-monomorphization even when they are unused.
//! (https://github.com/rust-lang/miri/issues/1382)
#![feature(never_type)]

struct PrintName<T>(T);
impl<T> PrintName<T> {
    // Change the constant to a function to defer evaluation to runtime.
    // Constants are evaluated during monomorphization if referenced, even in dead code.
    fn void() -> ! {
        panic!()
    }
}

fn no_codegen<T>() {
    if false {
        // Call the function instead of referencing the constant.
        let _ = PrintName::<T>::void();
    }
}

fn main() {
    no_codegen::<i32>();
}