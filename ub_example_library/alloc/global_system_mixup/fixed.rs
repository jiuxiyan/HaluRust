#![feature(allocator_api, slice_ptr_get)]

use std::alloc::{Allocator, Global, Layout};

fn main() {
    let l = Layout::from_size_align(1, 1).unwrap();
    let ptr = Global.allocate(l).unwrap().as_non_null_ptr();
    unsafe { Global.deallocate(ptr, l) };
}